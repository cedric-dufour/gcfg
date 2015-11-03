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

# Modules
# ... deb: python-argparse
from GCfg import \
    GCFG_VERSION, \
    GCfgExec
import argparse
import grp
import errno
import os
import pwd
from stat import *
import sys
import textwrap


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class GCfgPermissions(GCfgExec):
    """
    GIT-based Configuration Tracking Utility (GCFG) - Command 'permissions'
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
        GCfgExec._initArgumentParser(
            self,
            _sCommand,
            textwrap.dedent('''
                synopsis:
                  Show or change the permissions of the given file.
            ''')
        )

        # Additional arguments
        self._oArgumentParser.add_argument(
            'file', type=str, metavar='<file>',
            help='file to show/change the permissions of'
        )
        self._oArgumentParser.add_argument(
            'mode', type=str, metavar='<mode>', nargs='?',
            help='file mode (chmod-like) to set'
        )
        self._oArgumentParser.add_argument(
            'owner', type=str, metavar='<owner>', nargs='?',
            help='file owner (chown-like) to set'
        )


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    #
    # Helper
    #

    def filemode(self, mode):
        """
        Convert a file's mode to a string of the form '-rwxrwxrwx'.
        (COPIED FROM https://hg.python.org/cpython/file/3.3/Lib/stat.py; THIS FUNCTION IS __NOT__ COVERED BY GCFG COPYRIGHT)
        """

        filemode_table = (
            ((S_IFLNK, 'l'),
             (S_IFREG, '-'),
             (S_IFBLK, 'b'),
             (S_IFDIR, 'd'),
             (S_IFCHR, 'c'),
             (S_IFIFO, 'p')),

            ((S_IRUSR, 'r'),),
            ((S_IWUSR, 'w'),),
            ((S_IXUSR|S_ISUID, 's'),
             (S_ISUID, 'S'),
             (S_IXUSR, 'x')),

            ((S_IRGRP, 'r'),),
            ((S_IWGRP, 'w'),),
            ((S_IXGRP|S_ISGID, 's'),
             (S_ISGID, 'S'),
             (S_IXGRP, 'x')),

            ((S_IROTH, 'r'),),
            ((S_IWOTH, 'w'),),
            ((S_IXOTH|S_ISVTX, 't'),
             (S_ISVTX, 'T'),
             (S_IXOTH, 'x'))
        )
        perm = []
        for table in filemode_table:
            for bit, char in table:
                if mode & bit == bit:
                    perm.append(char)
                    break
            else:
                perm.append('-')
        return ''.join(perm)


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
        if not oGCfgLib.check(): return errno.EPERM
        (iMode, iUID, iGID) = oGCfgLib.permissions(
            self._oArguments.file,
            self._oArguments.mode,
            self._oArguments.owner
        )
        sys.stdout.write('%s/%s %s:%s %s\n' % (
            oct(iMode)[-4:], self.filemode(iMode),
            pwd.getpwuid(iUID)[0],
            grp.getgrgid(iGID)[0],
            self._oArguments.file
            )
        )
        return 0