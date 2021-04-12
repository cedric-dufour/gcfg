# -*- mode:python; tab-width:4; c-basic-offset:4; intent-tabs-mode:nil; -*-
# ex: filetype=python tabstop=4 softtabstop=4 shiftwidth=4 expandtab autoindent smartindent

#
# GIT-based Configuration Tracking Utility (GCFG)
# Copyright (C) 2015 Cedric Dufour <http://cedric.dufour.name>
# Author: Cedric Dufour <http://cedric.dufour.name>
#
# The GIT-based Configuration Tracking Utility (GCFG) is free software:
# you can redistribute it and/or modify it under the terms of the GNU General
# Public License as published by the Free Software Foundation, Version 3.
#
# The GIT-based Configuration Tracking Utility (GCFG) is distributed in the hope
# that it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
#
# See the GNU General Public License for more details.
#

import errno
import textwrap

from gcfg import GCfgBin


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class GCfgDelta(GCfgBin):
    """
    GIT-based Configuration Tracking Utility (GCFG) - Command 'delta'
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def _initArgumentParser(self, _sCommand=None):
        """
        Creates the arguments parser (and help generator)

        @param  string  _sCommand  Command name
        """

        # Parent
        GCfgBin._initArgumentParser(
            self,
            _sCommand,
            textwrap.dedent(r"""
                synopsis:
                  Show the differences between the given  file and its original content.
            """)
        )

        # Additional arguments
        self._oArgumentParser.add_argument(
            "file", type=str, metavar="<file>",
            help="file to show the differences for"
        )
        self._oArgumentParser.add_argument(
            "commentPrefix", type=str, metavar="<comment-prefix>", nargs="?",
            help="comment prefix (used to stripped commented lines out of the result)"
        )

    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    #
    # Main
    #

    def execute(self, _sCommand=None, _lArguments=None):
        """
        Executes

        @param  string  _sCommand    Command name
        @param  list    _lArguments  Command arguments

        @return integer  Exit code; non-zero in case of failure
        """

        # Arguments
        self._initArgumentParser(_sCommand)
        self._initArguments(_lArguments)

        # Handle command
        oGCfgLib = self._getLibrary()
        oGCfgLib.setDebug(self._oArguments.debug)
        oGCfgLib.setSilent(self._oArguments.silent)
        if not oGCfgLib.check():
            return errno.EPERM
        oGCfgLib.delta(
            self._oArguments.file,
            self._oArguments.commentPrefix,
            False
        )
        return 0
