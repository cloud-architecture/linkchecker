#!/usr/bin/env python
#******************************************************************************\
#* Copyright (c) 2003-2004, Martin Blais
#* All rights reserved.
#*
#* Redistribution and use in source and binary forms, with or without
#* modification, are permitted provided that the following conditions are
#* met:
#*
#* * Redistributions of source code must retain the above copyright
#*   notice, this list of conditions and the following disclaimer.
#*
#* * Redistributions in binary form must reproduce the above copyright
#*   notice, this list of conditions and the following disclaimer in the
#*   documentation and/or other materials provided with the distribution.
#*
#* * Neither the name of the Martin Blais, Furius, nor the names of its
#*   contributors may be used to endorse or promote products derived from
#*   this software without specific prior written permission.
#*
#* THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#* "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#* LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#* A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#* OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#* SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#* LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#* DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#* THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#* (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#* OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#******************************************************************************\

"""Automatic completion for optparse module.

This module provide automatic bash completion support for programs that use the
optparse module.  The premise is that the optparse options parser specifies
enough information (and more) for us to be able to generate completion strings
esily.  Another advantage of this over traditional completion schemes where the
completion strings are hard-coded in a separate bash source file, is that the
same code that parses the options is used to generate the completions, so the
completions is always up-to-date with the program itself.

In addition, we allow you specify a list of regular expressions or code that
define what kinds of files should be proposed as completions to this file if
needed.  If you want to implement more complex behaviour, you can instead
specify a function, which will be called with the current directory as an
argument.

You need to activate bash completion using the shell script function that comes
with optcomplete (see http://furius.ca/optcomplete for more details).

"""

__version__ = "$Revision$"
__author__ = "Martin Blais <blais@furius.ca>"

## Bash Protocol Description
## -------------------------
##
## `COMP_CWORD'
##      An index into `${COMP_WORDS}' of the word containing the current
##      cursor position.  This variable is available only in shell
##      functions invoked by the programmable completion facilities (*note
##      Programmable Completion::).
##
## `COMP_LINE'
##      The current command line.  This variable is available only in
##      shell functions and external commands invoked by the programmable
##      completion facilities (*note Programmable Completion::).
##
## `COMP_POINT'
##      The index of the current cursor position relative to the beginning
##      of the current command.  If the current cursor position is at the
##      end of the current command, the value of this variable is equal to
##      `${#COMP_LINE}'.  This variable is available only in shell
##      functions and external commands invoked by the programmable
##      completion facilities (*note Programmable Completion::).
##
## `COMP_WORDS'
##      An array variable consisting of the individual words in the
##      current command line.  This variable is available only in shell
##      functions invoked by the programmable completion facilities (*note
##      Programmable Completion::).
##
## `COMPREPLY'
##      An array variable from which Bash reads the possible completions
##      generated by a shell function invoked by the programmable
##      completion facility (*note Programmable Completion::).

#===============================================================================
# EXTERNAL DECLARATIONS
#===============================================================================

import sys
import os
import os.path
import types
import re
import pprint

#===============================================================================
# PUBLIC DECLARATIONS
#===============================================================================

debugfn = None # for debugging only

#-------------------------------------------------------------------------------
#
class AllCompleter:

    """Completes by listing all possible files in current directory."""

    def __call__( self, pwd, line, point, prefix, suffix ):
        return os.listdir(pwd)

#-------------------------------------------------------------------------------
#
class NoneCompleter:
    """Generates empty completion list."""

    def __call__( self, pwd, line, point, prefix, suffix ):
        return []

#-------------------------------------------------------------------------------
#
class DirCompleter:
    """Completes by listing subdirectories only."""

    def __call__( self, pwd, line, point, prefix, suffix ):
        return filter(os.path.isdir, os.listdir(pwd))

#-------------------------------------------------------------------------------
#
class RegexCompleter:
    """Completes by filtering all possible files with the given list of
    regexps."""

    def __init__( self, regexlist, always_dirs=True ):
        self.always_dirs = always_dirs

        if isinstance(regexlist, types.StringType):
            regexlist = [regexlist]
        self.regexlist = []
        for r in regexlist:
            if isinstance(r, types.StringType):
                r = re.compile(r)
            self.regexlist.append(r)

    def __call__( self, pwd, line, point, prefix, suffix ):
        dn = os.path.dirname(prefix)
        if dn:
            pwd = dn
        files = os.listdir(pwd)
        ofiles = []
        for fn in files:
            for r in self.regexlist:
                if r.match(fn):
                    if dn:
                        fn = os.path.join(dn, fn)
                    ofiles.append(fn)
                    break
            if self.always_dirs and os.path.isdir(fn):
                ofiles.append(fn + '/')
        return ofiles

#-------------------------------------------------------------------------------
#
class ListCompleter:

    """Completes by filtering using a fixed list of strings."""

    def __init__( self, stringlist ):
        self.olist = stringlist

    def __call__( self, pwd, line, point, prefix, suffix ):
        return self.olist

#-------------------------------------------------------------------------------
#
def extract_word( line, point ):

    """Return a prefix and suffix of the enclosing word.  The character under
    the cursor is the first character of the suffix."""

    wsre = re.compile('[ \t]')

    if point < 0 or point > len(line):
        return '', ''

    preii = point - 1
    while preii >= 0:
        if wsre.match(line[preii]):
            break
        preii -= 1
    preii += 1

    sufii = point
    while sufii < len(line):
        if wsre.match(line[sufii]):
            break
        sufii += 1

    return line[preii : point], line[point : sufii]

#-------------------------------------------------------------------------------
#
def autocomplete( parser,
                  arg_completer=None, # means use default.
                  opt_completer=None,
                  subcmd_completer=None,
                  subcommands=None ):

    """Automatically detect if we are requested completing and if so generate
    completion automatically from given parser.

    'parser' is the options parser to use.

    'file_completer' is a callable object that gets invoked to produce a list of
    completions for arguments completion (oftentimes files).

    'opt_completer' is the default completer to the options that require a
    value. 'subcmd_completer' is the default completer for the subcommand
    arguments.

    If 'subcommands' is specified, the script expects it to be a map of
    command-name to an object of any kind.  We are assuming that this object is
    a map from command name to a pair of (options parser, completer) for the
    command. If the value is not such a tuple, the method
    'autocomplete(completer)' is invoked on the resulting object.

    This will attempt to match the first non-option argument into a subcommand
    name and if so will use the local parser in the corresponding map entry's
    value.  This is used to implement completion for subcommand syntax and will
    not be needed in most cases."""

    # If we are not requested for complete, simply return silently, let the code
    # caller complete. This is the normal path of execution.
    if not os.environ.has_key('OPTPARSE_AUTO_COMPLETE'):
        return

    # Set default completers.
    if not arg_completer:
        arg_completer = AllCompleter()
    if not opt_completer:
        opt_completer = AllCompleter()
    if not subcmd_completer:
        subcmd_completer = arg_completer

    # By default, completion will be arguments completion, unless we find out
    # later we're trying to complete for an option.
    completer = arg_completer

    #
    # Completing...
    #

    # Fetching inputs... not sure if we're going to use these.
    cwords = os.environ['COMP_WORDS'].split()
    cline = os.environ['COMP_LINE']
    cpoint = int(os.environ['COMP_POINT'])
    cword = int(os.environ['COMP_CWORD'])


    # If requested, try subcommand syntax to find an options parser for that
    # subcommand.
    if subcommands:
        assert isinstance(subcommands, types.DictType)
        value = guess_first_nonoption(parser, subcommands)
        if value:
            if isinstance(value, types.ListType) or \
               isinstance(value, types.TupleType):
                parser = value[0]
                if len(value) > 1 and value[1]:
                    # override completer for command if it is present.
                    completer = value[1]
                else:
                    completer = subcmd_completer
                return autocomplete(parser, completer)
            else:
                # Call completion method on object. This should call
                # autocomplete() recursively with appropriate arguments.
                if hasattr(value, 'autocomplete'):
                    return value.autocomplete(subcmd_completer)
                else:
                    sys.exit(1) # no completions for that command object

    # Extract word enclosed word.
    prefix, suffix = extract_word(cline, cpoint)
    # The following would be less exact, but will work nonetheless .
    # prefix, suffix = cwords[cword], None

    # Look at previous word, if it is an option and it requires an argument,
    # check for a local completer.  If there is no completer, what follows
    # directly cannot be another option, so mark to not add those to
    # completions.
    optarg = False
    try:
        # Look for previous word, which will be containing word if the option
        # has an equals sign in it.
        prev = None
        if cword < len(cwords):
            mo = re.search('(--.*)=(.*)', cwords[cword])
            if mo:
                prev, prefix = mo.groups()
        if not prev:
            prev = cwords[cword - 1]

        if prev and prev.startswith('-'):
            option = parser.get_option(prev)
            if option:
                if option.nargs > 0:
                    optarg = True
                    if hasattr(option, 'completer'):
                        completer = option.completer
                    else:
                        completer = opt_completer
                # Warn user at least, it could help him figure out the problem.
                elif hasattr(option, 'completer'):
                    raise SystemExit(
                        "Error: optparse option with a completer "
                        "does not take arguments: %s" % str(option))
    except KeyError:
        pass

    completions = []

    # Options completion.
    if not optarg and (not prefix or prefix.startswith('-')):
        completions += parser._short_opt.keys()
        completions += parser._long_opt.keys()
        # Note: this will get filtered properly below.

    # File completion.
    if completer and (not prefix or not prefix.startswith('-')):

        # Call appropriate completer depending on type.
        if isinstance(completer, types.StringType) or \
               isinstance(completer, types.ListType) or \
               isinstance(completer, types.TupleType):

            completer = RegexCompleter(completer)
            completions += completer(os.getcwd(), cline, cpoint, prefix, suffix)

        elif isinstance(completer, types.FunctionType) or \
             isinstance(completer, types.LambdaType) or \
             isinstance(completer, types.ClassType) or \
             isinstance(completer, types.ObjectType):
            completions += completer(os.getcwd(), cline, cpoint, prefix, suffix)

    # Filter using prefix.
    if prefix:
        completions = filter(lambda x: x.startswith(prefix), completions)

    # Print result.
    print ' '.join(completions)

    # Print debug output (if needed).  You can keep a shell with 'tail -f' to
    # the log file to monitor what is happening.
    if debugfn:
        f = open(debugfn, 'a')
        print >> f, '---------------------------------------------------------'
        print >> f, 'CWORDS', cwords
        print >> f, 'CLINE', cline
        print >> f, 'CPOINT', cpoint
        print >> f, 'CWORD', cword
        print >> f, '\nShort options'
        print >> f, pprint.pformat(parser._short_opt)
        print >> f, '\nLong options'
        print >> f, pprint.pformat(parser._long_opt)
        print >> f, 'Prefix/Suffix:', prefix, suffix
        print >> f, 'completions', completions
        f.close()

    # Exit with error code (we do not let the caller continue on purpose, this
    # is a run for completions only.)
    sys.exit(1)

#-------------------------------------------------------------------------------
#
def guess_first_nonoption( gparser, subcmds_map ):

    """Given a global options parser, try to guess the first non-option without
    generating an exception. This is used for scripts that implement a
    subcommand syntax, so that we can generate the appropriate completions for
    the subcommand."""

    import copy
    gparser = copy.deepcopy(gparser)
    def print_usage_nousage (self, file=None):
        pass
    gparser.print_usage = print_usage_nousage

    prev_interspersed = gparser.allow_interspersed_args # save state to restore
    gparser.disable_interspersed_args()

    cwords = os.environ['COMP_WORDS'].split()

    try:
        gopts, args = gparser.parse_args(cwords[1:])
    except SystemExit:
        return None

    value = None
    if args:
        subcmdname = args[0]
        try:
            value = subcmds_map[subcmdname]
        except KeyError:
            pass

    gparser.allow_interspersed_args = prev_interspersed # restore state

    return value # can be None, indicates no command chosen.

#-------------------------------------------------------------------------------
#
class CmdComplete:

    """Simple default base class implementation for a subcommand that supports
    command completion.  This class is assuming that there might be a method
    addopts(self, parser) to declare options for this subcommand, and an
    optional completer data member to contain command-specific completion.  Of
    course, you don't really have to use this, but if you do it is convenient to
    have it here."""

    def autocomplete( self, completer ):
        import optparse
        parser = optparse.OptionParser(self.__doc__.strip())
        if hasattr(self, 'addopts'):
            self.addopts(parser)
        if hasattr(self, 'completer'):
            completer = self.completer
        return autocomplete(parser, completer)

#===============================================================================
# TEST
#===============================================================================

def test():
    print extract_word("extraire un mot d'une phrase", 11)
    print extract_word("extraire un mot d'une phrase", 12)
    print extract_word("extraire un mot d'une phrase", 13)
    print extract_word("extraire un mot d'une phrase", 14)
    print extract_word("extraire un mot d'une phrase", 0)
    print extract_word("extraire un mot d'une phrase", 28)
    print extract_word("extraire un mot d'une phrase", 29)
    print extract_word("extraire un mot d'une phrase", -2)
    print extract_word("optcomplete-test do", 19)

if __name__ == '__main__':
    test()
