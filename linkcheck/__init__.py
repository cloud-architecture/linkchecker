# -*- coding: iso-8859-1 -*-
"""main function module for link checking"""
# Copyright (C) 2000-2004  Bastian Kleineidam
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import sys
import re
import time

from linkcheck.i18n import _

import httplib2

# logger areas
LOG = "linkcheck"
LOG_CMDLINE = "linkcheck.cmdline"
LOG_CHECK = "linkcheck.check"
LOG_GUI = "linkcheck.gui"
lognames = {
    "cmdline": LOG_CMDLINE,
    "checking": LOG_CHECK,
    "gui": LOG_GUI,
    "all": LOG,
    }
lognamelist = ", ".join(["%r"%name for name in lognames.keys()])


class LinkCheckerError (Exception):
    """exception to be raised on linkchecker-specific check errors"""
    pass


def get_link_pat (arg, strict=False):
    """get a link pattern matcher for intern/extern links"""
    linkcheck.log.debug(LOG_CHECK, "Link pattern %r", arg)
    if arg[0:1] == '!':
        pattern = arg[1:]
        negate = True
    else:
        pattern = arg
        negate = False
    return {
        "pattern": re.compile(pattern),
        "negate": negate,
        "strict": strict,
    }


import linkcheck.logger.standard
import linkcheck.logger.html
import linkcheck.logger.colored
import linkcheck.logger.gml
import linkcheck.logger.sql
import linkcheck.logger.csvlog
import linkcheck.logger.blacklist
import linkcheck.logger.xmllog
import linkcheck.logger.none


# default logger classes
Loggers = {
    "text": linkcheck.logger.standard.StandardLogger,
    "html": linkcheck.logger.html.HtmlLogger,
    "colored": linkcheck.logger.colored.ColoredLogger,
    "gml": linkcheck.logger.gml.GMLLogger,
    "sql": linkcheck.logger.sql.SQLLogger,
    "csv": linkcheck.logger.csvlog.CSVLogger,
    "blacklist": linkcheck.logger.blacklist.BlacklistLogger,
    "xml": linkcheck.logger.xmllog.XMLLogger,
    "none": linkcheck.logger.none.NoneLogger,
}
# for easy printing: a comma separated logger list
LoggerKeys = ", ".join(["%r"%name for name in Loggers.keys()])
