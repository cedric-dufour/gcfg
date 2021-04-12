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

import argparse
import errno
import os
import pwd
import socket
import sys
import textwrap

from gcfg import GCFG_VERSION, GCfgLib


# Constants
GCFG_COMMANDS = {
    "init": "GCfgInit",
    "verify": "GCfgVerify",
    "list": "GCfgList",
    "add": "GCfgAdd",
    "new": "GCfgAdd",
    "copy": "GCfgCopy",
    "cp": "GCfgCopy",
    "move": "GCfgMove",
    "mv": "GCfgMove",
    "remove": "GCfgRemove",
    "rm": "GCfgRemove",
    "edit": "GCfgEdit",
    "permissions": "GCfgPermissions",
    "perm": "GCfgPermissions",
    "chmod": "GCfgPermissions",
    "chown": "GCfgPermissions",
    "flag": "GCfgFlag",
    "unflag": "GCfgUnflag",
    "flagged": "GCfgFlagged",
    "original": "GCfgOriginal",
    "orig": "GCfgOriginal",
    "delta": "GCfgDelta",
    "pkglist": "GCfgPkgList",
    "pkgsave": "GCfgPkgSave",
    "pkgdiff": "GCfgPkgDiff",
    "git": "GCfgGit",
    "a2ps": "GCfgA2ps"
}


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class GCfgBin:
    """
    GIT-based Configuration Tracking Utility (GCFG) - Command wrapper
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def _initArgumentParser(self, _sCommand=None, _sSynopsis=None):
        """
        Creates the arguments parser (and help generator)

        @param  string  _sCommand  Command name
        @param  string  _sSynopsis   Additional help (synopsis)
        """

        # Command
        if _sCommand is None:
            _sCommand = sys.argv[0].split(os.sep)[-1]

        # Create argument parser
        if _sSynopsis is None:
            self._oArgumentParser = argparse.ArgumentParser(
                prog=_sCommand
            )
        else:
            self._oArgumentParser = argparse.ArgumentParser(
                prog=_sCommand,
                formatter_class=argparse.RawDescriptionHelpFormatter,
                epilog=_sSynopsis
            )

        # Standard arguments
        self._addOptionVersion(self._oArgumentParser)
        self._addOptionDebug(self._oArgumentParser)
        self._addOptionSilent(self._oArgumentParser)

    def _initArguments(self, _lArguments=None, _bAllowUnknownArguments=False):
        """
        Parses the command-line arguments.

        @param  list     _lArguments              Command arguments
        @param  boolean  _bAllowUnknownArguments  Allow unknown arguments

        @return list  List of unknown arguments (if allowed)
        """

        # Parse arguments
        lUnknownArguments = []
        if _bAllowUnknownArguments:
            (self._oArguments, lUnknownArguments) = self._oArgumentParser.parse_known_args(_lArguments)
        else:
            self._oArguments = self._oArgumentParser.parse_args(_lArguments)
        self._convertLegacyOptions(self._oArguments)
        return lUnknownArguments

    def _addOptionVersion(self, _oArgumentParser):
        """
        Adds the '--version' option to the given argument parser
        """

        # Add argument
        _oArgumentParser.add_argument(
            "-v", "--version", action="version",
            version=("GCFG - %s - Cedric Dufour <http://cedric.dufour.name>\n" % GCFG_VERSION)
        )

    def _addOptionDebug(self, _oArgumentParser):
        """
        Adds the '--debug' option to the given argument parser
        """

        # Add argument
        _oArgumentParser.add_argument(
            "-d", "--debug", action="store_true",
            help="show debug (and all other) messages"
        )

    def _addOptionSilent(self, _oArgumentParser):
        """
        Adds the '--silent' option to the given argument parser
        """

        # Add argument
        _oArgumentParser.add_argument(
            "-s", "--silent", action="store_true",
            help="mute all informational and warning messages"
        )

    def _addOptionBatch(self, _oArgumentParser):
        """
        Adds the '--batch' option to the given argument parser
        """

        # Add argument
        _oArgumentParser.add_argument(
            "-b", "--batch", action="store_true",
            help="suppress all confirmation messages"
        )

    def _addOptionForce(self, _oArgumentParser):
        """
        Adds the '--force' option to the given argument parser
        """

        # Add argument
        _oArgumentParser.add_argument(
            "-f", "--force", action="store_true",
            help="force default choices/actions in batch mode"
        )

    def _addOptionLink(self, _oArgumentParser):
        """
        Adds the '--link' option to the given argument parser
        """

        # Add argument
        _oArgumentParser.add_argument(
            "-L", "--link", type=str, choices=["hardlink", "symlink", "copy"],
            help="force link type"
        )
        # ... legacy support
        _oArgumentParser.add_argument(
            "--hard", action="store_true",
            help="force hardlink (deprecated; use --link instead)"
        )
        _oArgumentParser.add_argument(
            "--symbolic", action="store_true",
            help="force symlink (deprecated; use --link instead)"
        )
        _oArgumentParser.add_argument(
            "--copy", action="store_true",
            help="force copy (deprecated; use --link instead)"
        )

    def _convertLegacyOptions(self, _oArguments):
        if hasattr(_oArguments, "hard") and _oArguments.hard:
            _oArguments.link = "hardlink"
        elif hasattr(_oArguments, "symbolic") and _oArguments.symbolic:
            _oArguments.link = "symlink"
        elif hasattr(_oArguments, "copy") and _oArguments.copy:
            _oArguments.link = "copy"

    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    def _help(self):
        sys.stdout.write(
            textwrap.dedent(r"""
                commands:
                  init:
                    Initializes the configuration repository

                  verify:
                    Verify the consistency of the configuration repository (links)

                  list:
                    List the files in the configuration repository

                  add (new), copy (cp), move (mv), remove (rm):
                    Add, copy, move or remove a file in the configuration repository

                  edit:
                    Edit a file (after adding it to the configuration repository)

                  permissions (perm, chmod, chown):
                    Show/change the permissions of a file

                  flag, unflag, flagged:
                    Add, remove or check/retrieve a flag to/from a file

                  original (orig):
                    Show the original content of a file

                  delta:
                    Show the differences between a file and its original content

                  pkglist, pkgsave, pkgdiff:
                    Display, save or diff the list of installed packages

                  git:
                    Perform the corresponding command within the GIT sub-repository

                  a2ps:
                    Create a Postscript document with all files in the configuration repository

                further help:
                  gcfg <command> --help
            """)
        )

    def _getLibrary(self):
        return GCfgLib(
            os.getenv("GCFG_AUTHOR", pwd.getpwuid(os.getuid())[0]),
            os.getenv("GCFG_EMAIL", "%s@%s" % (pwd.getpwuid(os.getuid())[0], socket.gethostbyaddr(socket.gethostname())[0])),
            os.getenv("GCFG_ROOT", "/etc/gcfg")
        )

    #
    # Main
    #

    def execute(self):
        """
        Executes; returns a non-zero exit code in case of failure.
        """

        try:

            # Parse command line
            sCommand = None
            lArguments = []
            for i in range(1, len(sys.argv)):
                s = sys.argv[i]
                if sCommand is None and s[0] != "-":
                    sCommand = s
                    continue
                lArguments += [s]

            # Instantiate command
            cCommand = GCFG_COMMANDS[sCommand]
            oCommand = getattr(__import__("gcfg.%s" % sCommand, fromlist=["gcfg"]), cCommand)

        except (IndexError, KeyError):
            sys.stdout.write("usage: gcfg <command>\n")
            if len(sys.argv) <= 1:
                sys.stdout.write("error: too few arguments\n")
            elif sys.argv[1] in ["help", "--help", "-h"]:
                self._help()
                return 0
            else:
                sys.stdout.write("error: invalid command\n")
            return errno.EINVAL

        # Execute command
        try:
            return oCommand().execute(sCommand, lArguments)
        except EnvironmentError as e:
            return e.errno
