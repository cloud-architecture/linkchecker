# -*- coding: iso-8859-1 -*-
# Copyright (C) 2006 Bastian Kleineidam
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
"""
Management of checking a queue of links with several threads.
"""
import time
import linkcheck
import linkcheck.log
import linkcheck.cache.urlqueue
import linkcheck.cache.robots_txt
import linkcheck.cache.cookie
import linkcheck.cache.connection
import aggregator
import console


def check_urls (aggregate):
    """
    Main check function; checks all configured URLs until interrupted
    with Ctrl-C.
    @return: None
    """
    try:
        aggregate.logger.start_log_output()
        if not aggregate.urlqueue.empty():
            aggregate.start_threads()
        # Since urlqueue.join() is not interruptable, add a timeout
        # and a one-second slumber.
        while True:
            try:
                aggregate.urlqueue.join(timeout=1)
                break
            except linkcheck.cache.urlqueue.Timeout:
                time.sleep(1)
                aggregate.remove_stopped_threads()
                if not aggregate.threads:
                    break
    except KeyboardInterrupt:
        linkcheck.log.warn(linkcheck.LOG_CHECK,
            _("keyboard interrupt; waiting for active threads to finish"))
        aggregate.abort()
    except:
        console.internal_error()
        aggregate.abort()
    aggregate.finish()
    aggregate.logger.end_log_output()


def get_aggregate (config):
    """
    Get an aggregator instance with given configuration.
    """
    urlqueue = linkcheck.cache.urlqueue.UrlQueue()
    connections = linkcheck.cache.connection.ConnectionPool(wait=config["wait"])
    cookies = linkcheck.cache.cookie.CookieJar()
    robots_txt = linkcheck.cache.robots_txt.RobotsTxt()
    return aggregator.Aggregate(config, urlqueue, connections,
                                cookies, robots_txt)
