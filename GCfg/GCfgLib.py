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
import argparse
import errno
import inspect
import subprocess
import os
import re
import shutil
import sys
import tempfile


#------------------------------------------------------------------------------
# CLASSES
#------------------------------------------------------------------------------

class GCfgLib:
    """
    GIT-based Configuration Tracking Utility (GCFG) - Core Library
    """

    #------------------------------------------------------------------------------
    # CONSTRUCTORS / DESTRUCTOR
    #------------------------------------------------------------------------------

    def __init__(self, _sAuthor, _sEmail, _sRoot):
        # Properties (arguments)
        self.__sAuthor = _sAuthor
        self.__sEmail = _sEmail
        self.__sRoot = _sRoot
        # ... on *nix system, use 'pwd' as (current) working directory (without symlinks being dereferenced)
        oPopen = subprocess.Popen('pwd', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (sStdOut, sStdErr) = oPopen.communicate()
        if (oPopen.returncode==0):
            self.__sWorkingDirectory = sStdOut.splitlines()[0]
        else:
            self.__sWorkingDirectory = os.getcwd()

        # Properties (internal)
        self.__bDebug = False
        self.__bSilent = False
        self.__asSubRepositories = {}
        # ... regular expressions
        self.__rePathCron = re.compile('.*%scron\..*%s.*' % (re.escape(os.sep), re.escape(os.sep)))
        self.__reFileText = re.compile('(^| )text( |$)')


    #------------------------------------------------------------------------------
    # METHODS
    #------------------------------------------------------------------------------

    #
    # Output messages handling
    #

    def _ERROR(self, _sMessage):
        """
        Write the given error message to the standard error output.

        @param  string  _sMessage  Error message
        """
        sys.stderr.write('ERROR[%s]: %s\n' % (inspect.currentframe().f_back.f_code.co_name.lstrip('_'), _sMessage))


    def _WARNING(self, _sMessage):
        """
        Write the given warning message to the standard error output.

        @param  string  _sMessage  Warning message
        """
        if not self.__bSilent:
            sys.stderr.write('WARNING[%s]: %s\n' % (inspect.currentframe().f_back.f_code.co_name.lstrip('_'), _sMessage))


    def _INFO(self, _sMessage):
        """
        Write the given informational message to the standard output.

        @param  string  _sMessage  Informational message
        """
        if not self.__bSilent:
            sys.stdout.write('INFO[%s]: %s\n' % (inspect.currentframe().f_back.f_code.co_name.lstrip('_'), _sMessage))


    def _DEBUG(self, _sMessage):
        """
        Write the given debug message to the standard output.

        @param  string  _sMessage  Debug message
        """
        if self.__bDebug:
            sys.stdout.write('DEBUG[%s]: %s\n' % (inspect.currentframe().f_back.f_code.co_name, _sMessage))

    #
    # API (helpers)
    #

    def setDebug(self, _bDebug):
        """
        Show debug (and all other) messages.

        @param  bool  _bDebug  Debug status
        """

        self.__bDebug = _bDebug
        self.__bSilent = False


    def setSilent(self, _bSilent):
        """
        Mute all informational and warning messages.

        @param  bool  _bSilent  Silent status
        """

        if not self.__bDebug:
            self.__bSilent = _bSilent


    def _confirm(self, _sPrompt, _lOptions, _sOptionDefault=None):
        """
        Display the given prompt and available options, waits for valid input
        and returns the selected option.

        @param  string  _sPrompt         Prompt text
        @param  list    _lOptions        Available options
        @param  string  _sOptionDefault  Default option choice

        @return string  Choosen option
        """

        # Options
        sOptionDefault = _sOptionDefault
        if sOptionDefault is not None:
            sOptionDefault = sOptionDefault.lower()
        lOptions = []
        for sOption in _lOptions:
            if sOption==_sOptionDefault:
                lOptions += sOption.upper()
            else:
                lOptions += sOption.lower()

        # Prompt
        sPrompt = 'CONFIRM[%s]: %s [%s] ? ' % (inspect.currentframe().f_back.f_code.co_name.lstrip('_'), _sPrompt, '/'.join(lOptions))

        # Input
        while True:
            sys.stdout.write(sPrompt)
            sChoice = raw_input().lower()
            if not sChoice and sOptionDefault is not None:
                sChoice = sOptionDefault
            if sChoice in lOptions or sChoice==sOptionDefault:
                return sChoice


    def _dirpath(self, _sPath):
        """
        Return the (parent) directory path from the given path.

        @param  string  _sPath  File/directory path

        @return string  (Parent) directory path
        """

        sDirname = os.path.dirname(_sPath)
        if not sDirname: sDirname = '.'
        return sDirname


    def _mkdir(self, _sDirectory):
        """
        Create the given directory (recursively).

        @param  string  _sDirectory  Directory path
        """

        self._DEBUG('Creating directory; %s' % _sDirectory)
        os.makedirs(_sDirectory)


    def mkdir(self, _sDirectory):
        """
        Create the given directory (recursively).
        (including validation and exceptions handling)

        @param  string  _sDirectory  Directory path
        """

        try:

            # Create directory
            if not os.path.isdir(_sDirectory):
                self._mkdir(_sDirectory)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sDirectory))
            raise EnvironmentError(e.errno, 'Failed to create directory')


    def _rmdir(self, _sDirectory):
        """
        Remove the given directory (recursively).

        @param  string  _sDirectory  Directory path
        """

        self._DEBUG('Removing directory; %s' % _sDirectory)
        try:
            os.removedirs(_sDirectory)
        except OSError as e:
            pass


    def rmdir(self, _sDirectory):
        """
        Remove the given directory (recursively).
        (including validation and exceptions handling)

        @param  string  _sDirectory  Directory path
        """

        try:

            # Remove directory
            if os.path.isdir(_sDirectory):
                self._rmdir(_sDirectory)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sDirectory))
            raise EnvironmentError(e.errno, 'Failed to remove directory')


    def _cp(self, _sSource, _sDestination):
        """
        Copy the specified source file/directory to the specified destination file/directory.

        @param  string  _sSource       Source file/directory path
        @param  string  _sDestination  Destination file/directory path
        """

        self._DEBUG('Copying file/directory; %s => %s' % (_sSource, _sDestination))
        oStat = os.stat(_sSource)
        shutil.copy2(_sSource, _sDestination)
        try:
            os.chown(_sDestination, oStat.st_uid, oStat.st_gid)
        except OSError as e:
            self._WARNING('Failed to preserve file ownership; %s => %s' % (_sSource, _sDestination))


    def _mv(self, _sSource, _sDestination):
        """
        Move the specified source file/directory to the specified destination file/directory.

        @param  string  _sSource       Source file/directory path
        @param  string  _sDestination  Destination file/directory path
        """

        self._DEBUG('Moving file/directory; %s => %s' % (_sSource, _sDestination))
        oStat = os.stat(_sSource)
        shutil.move(_sSource, _sDestination)
        try:
            os.chown(_sDestination, oStat.st_uid, oStat.st_gid)
        except OSError as e:
            self._WARNING('Failed to preserve file ownership; %s => %s' % (_sSource, _sDestination))


    def _rm(self, _sFile):
        """
        Remove (unlink) the specified file.

        @param  string  _sFile  File to remove
        """

        self._DEBUG('Removing file; %s' % _sFile)
        os.unlink(_sFile)


    def _shellCommand(self, _lCommand, _sWorkingDirectory=None, _bRedirectStdOut=True, _bIgnoreReturnCode=False):
        """
        Execute the given shell command, within the given working directory,
        and returns the resulting standard output

        @param  list    _lCommand           Executable path and arguments (as passed to Popen)
        @param  string  _sWorkingDirectory  Directory to switch to before executing the command
        @param  bool    _bRedirectStdOut    Redirect standard output
        @param  bool    _bIgnoreReturnCode  Do not raise error in case of non-zero return code

        @return string  Resulting standard output (if redirected)
        """

        # Execute shell command
        self._DEBUG('Executing shell command; %s: %s' % (_sWorkingDirectory, ' '.join(_lCommand)))
        if _bRedirectStdOut:
            oPopen = subprocess.Popen(
                _lCommand,
                cwd=_sWorkingDirectory,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
        else:
            oPopen = subprocess.Popen(
                _lCommand,
                cwd=_sWorkingDirectory,
                stderr=subprocess.PIPE
            )
        (sStdOut, sStdErr) = oPopen.communicate()
        if not _bIgnoreReturnCode and oPopen.returncode!=0:
            raise EnvironmentError(oPopen.returncode, sStdErr)
        return sStdOut


    def getCanonicalPath(self, _sPath, _bAllowDirectory=False):
        """
        Return the canonical path matching the given input path.
        If the path does not exists, its canonical equivalent is returned
        based on the parent directory canonical path.
        (including validation and exceptions handling)

        @param  string  _sPath            File/directory path
        @param  bool    _bAllowDirectory  Allow path to be a directory

        @return string  Absolute and canonical path
        """

        try:

            # Call stat() to raise any OS-level exception (permission denied, no such file, etc.)
            sParent = self._dirpath(_sPath)
            if not sParent: sParent = '.'
            if os.path.exists(_sPath):
                os.stat(_sPath)
            elif os.path.isdir(sParent):
                os.stat(sParent)
            else:
                raise EnvironmentError(errno.ENOENT, 'No such file or directory')

            # Return canonical path
            if os.path.isfile(_sPath) or not os.path.exists(_sPath):
                # ... for a (potentially not existing) file
                return os.path.join(
                    os.path.normpath(os.path.join(self.__sWorkingDirectory,sParent)),
                    os.path.basename(_sPath)
                )
            elif _bAllowDirectory and os.path.isdir(_sPath):
                # ... for a directory (if allowed)
                return os.path.normpath(os.path.join(self.__sWorkingDirectory,_sPath))
            else:
                # ... for neither directory nor file
                raise EnvironmentError(errno.ENOENT, 'Invalid path')

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sPath))
            raise EnvironmentError(e.errno, 'Failed to retrieve canonical path')


    def _getRepositoryPath(self, _sRepository, _sFileActual=None):
        """
        Return the sub-repository path matching the given (actual) file.

        @param  string  _sRepository  Sub-repository name (among: 'git', 'original', 'flag' or 'pkglist')
        @param  string  _sFileActual  Actual file (canonical path)

        @return string  Absolute/canonical sub-repository file path
        """

        sPath = self.__asSubRepositories[_sRepository]
        if _sFileActual is not None:
            sPath = os.path.join(sPath, _sFileActual.lstrip(os.sep))
        return sPath


    def getRepositoryPath(self, _sRepository, _sFileActual=None):
        """
        Return the sub-repository path matching the given (actual) file.
        (including validation and exceptions handling)

        @param  string  _sRepository  Sub-repository name (among: 'git', 'original', 'flag' or 'pkglist')
        @param  string  _sFileActual  Actual file (path)

        @return string  Absolute/canonical sub-repository file path
        """

        try:

            # Paths
            if _sFileActual is not None:
                _sFileActual = self.getCanonicalPath(_sFileActual)

            # Repository path
            return self._getRepositoryPath(_sRepository, _sFileActual)

        except IndexError as e:
            raise EnvironmentError(errno.EINVAL, 'Invalid repository; %s' % _sRepository)


    def _isLinked(self, _sFileGIT, _sFileActual):
        """
        Return whether the given GIT file is correctly linked (matches) with
        the given actual file.

        @param  string  _sFileGIT     File (canonical path) within GIT sub-repository
        @param  string  _sFileActual  Actual file (canonical path)

        @return tuple(bool,string)  Match status and link type
        """

        # Symlink ?
        self._DEBUG('Checking file is symkink; %s' % _sFileActual)
        if os.path.islink(_sFileActual):
            if not os.path.exists(_sFileActual) or not os.path.realpath(_sFileActual)==_sFileGIT:
                return (False, 'symlink')
            return (True, 'symlink')

        # File existency
        self._DEBUG('Checking file existency; %s <=> %s' % (_sFileActual, _sFileGIT))
        if not os.path.exists(_sFileGIT) or not os.path.exists(_sFileActual):
            return (False, None)

        # Hardlink ?
        self._DEBUG('Checking file is hardlink; %s' % _sFileActual)
        oStatGIT = os.stat(_sFileGIT)
        oStatActual = os.stat(_sFileActual)
        if oStatGIT.st_dev==oStatActual.st_dev and oStatGIT.st_ino==oStatActual.st_ino:
            return (True, 'hardlink')

        # Copy ?
        self._DEBUG('Checking file is copy; %s' % _sFileActual)
        if not oStatGIT.st_size==oStatActual.st_size:
            return (False, 'copy')
        with open(_sFileGIT, 'rb', 65536) as fFileGIT:
            with open(_sFileActual, 'rb', 65536) as fFileActual:
                while True:
                    sReadGIT = fFileGIT.read(65536)
                    sReadActual = fFileActual.read(65536)
                    if not sReadGIT==sReadActual:
                        return (False, 'copy')
                    if sReadGIT=='':
                        return (True, 'copy')


    def isLinked(self, _sFileActual):
        """
        Return whether the given actual file is correctly linked (matches) with
        its GIT sibling.
        (including exceptions handling)

        @param  string  _sFileActual  Actual file (path)

        @return tuple(bool,string)  Match status and link type
        """

        sFileGIT = None
        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Linked ?
            return self._isLinked(sFileGIT, sFileActual)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to compare files')


    def _link(self, _sFileGIT, _sFileActual, _sLink=None, _bBatch=False, _bForce=False):
        """
        Link the given GIT file with the given actual file, after validating and using
        the given link type.
        By default (if the link type is ommitted), 'hardlink' will be used, unless:
         - the file to track is in a special directory; e.g. cron-related directory => 'symlink'
         - the link crosses filesystem boundaries => 'copy'

        @param  string  _sFileGIT     File (canonical path) within GIT sub-repository
        @param  string  _sFileActual  Actual file (canonical path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode

        @return string  Created link type; None no link was created
        """

        # Paths
        sDirGIT = self._dirpath(_sFileGIT)
        sDirActual = self._dirpath(_sFileActual)

        # Check
        if not os.path.exists(sDirGIT):
            self._DEBUG('Creating GIT directory; %s' % sDirGIT)
            self._mkdir(sDirGIT)

        # Validate link type
        self._DEBUG('Validating link type; %s' % _sLink)
        sLink_validated = _sLink
        if sLink_validated is None:
            sLink_validated = 'hardlink'
        if os.stat(sDirGIT).st_dev!=os.stat(sDirActual).st_dev:
            sLink_validated = 'copy'
        elif self.__rePathCron.search(_sFileActual) is not None:
            sLink_validated = 'symlink'
        if _sLink is not None and sLink_validated!=_sLink:
            self._WARNING('Link type overridden; %s => %s' % (_sLink, sLink_validated))
            if not _bBatch:
                if self._confirm('Use overridden link type', ['y','n'])!='y':
                    return None
            elif not _bForce:
                raise EnvironmentError(errno.EPERM, 'Cannot change link type (unless forced)')
        self._DEBUG('=> %s' % sLink_validated)

        # Linked ?
        self._DEBUG('Checking file link (and type); %s -> %s' % (_sFileActual, _sFileGIT))
        (bLinked, sLink_actual) = self._isLinked(_sFileGIT, _sFileActual)
        self._DEBUG('=> %s (%s)' % (bLinked, sLink_actual))
        # ... link type
        if _sLink is not None and sLink_actual is not None and not sLink_actual==sLink_validated:
            self._WARNING('Link type differs; %s (%s <> %s)' % (_sFileActual, sLink_actual, sLink_validated))
            if not _bBatch:
                if self._confirm('Replace existing link', ['y','n'])!='y':
                    return None
            elif not _bForce:
                    raise EnvironmentError(errno.EPERM, 'Cannot replace existing link (unless forced)')
        elif bLinked:
            return None

        # Inconsistency ('copy'-linked files differ or missing GIT/actual file)
        bUseFileActual = None
        if not bLinked and os.path.exists(_sFileGIT):
            if not _bBatch:
                if os.path.exists(_sFileActual):
                    self._WARNING('File differs from its GIT sibling (copy); %s' % _sFileActual)
                    sPrompt = 'Show [D]ifferences, use [G]IT/[E]xisting file, [P]urge or [S]kip'
                    lChoices = ['d','g','e','p','s']
                else:
                    self._WARNING('File is missing; %s' % _sFileActual)
                    sPrompt = 'Use [G]IT file, [P]urge or [S]kip'
                    lChoices = ['g','p','s']
                while True:
                    sConfirm = self._confirm(sPrompt, lChoices)
                    if sConfirm=='s':
                        return None
                    if sConfirm=='p':
                        self.remove(_sFileActual, True, True)
                        return None
                    elif sConfirm=='e':
                        bUseFileActual = True
                        break
                    elif sConfirm=='g':
                        bUseFileActual = False
                        break
                    elif sConfirm=='d':
                        self._shellCommand(['diff', '-uN', '--label', 'GIT', _sFileGIT, _sFileActual], None, False, True)
            else:
                if not _bForce:
                    raise EnvironmentError(errno.EPERM, 'Cannot update differing files (unless forced)')
                bUseFileActual = os.path.exists(_sFileActual)

        # Move/create GIT file
        if bUseFileActual==True:
            self._DEBUG('Updating GIT file; %s => %s' % (_sFileActual, _sFileGIT))
            self._rm(_sFileGIT)
            self._cp(os.path.realpath(_sFileActual), _sFileGIT)
            self._rm(_sFileActual)
        elif bUseFileActual==False:
            self._DEBUG('Using existing GIT file; %s' % _sFileGIT)
            if os.path.exists(_sFileActual):
                if not _bBatch:
                    if self._confirm('Save original file', ['y','n'], 'n')=='y':
                        self.saveFileOriginal(_sFileActual, _sFileActual, True, True)
                self._rm(_sFileActual)
        elif os.path.exists(_sFileActual):
            if bLinked:
                self._DEBUG('Using existing GIT file; %s' % _sFileGIT)
            else:
                self._DEBUG('Creating GIT file; %s => %s' % (_sFileActual, _sFileGIT))
                self._cp(os.path.realpath(_sFileActual), _sFileGIT)
            self._rm(_sFileActual)
        elif not os.path.exists(_sFileGIT):
            self._DEBUG('Creating blank GIT file; %s' % _sFileGIT)
            with open(_sFileGIT, 'w') as fFileGIT:
                pass

        # Link
        self._DEBUG('Linking file; %s -> %s (%s)' % (_sFileActual, _sFileGIT, sLink_validated))
        if sLink_validated=='hardlink':
            os.link(_sFileGIT, _sFileActual)
        elif sLink_validated=='symlink':
            os.symlink(_sFileGIT, _sFileActual)
        elif sLink_validated=='copy':
            self._cp(_sFileGIT, _sFileActual)
        else:
            # Something's very wrong...
            raise Exception('Invalid link type; %s' % sLink_validated)
        return sLink_validated


    def link(self, _sFileActual, _sLink=None, _bBatch=False, _bForce=False):
        """
        Link the given actual file to its GIT sibling, after validating and using
        the given link type.
        By default (if the link type is ommitted), 'hardlink' will be used, unless:
         - the file to track is in a special directory; e.g. cron-related directory => 'symlink'
         - the link crosses filesystem boundaries => 'copy'
        (including informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode

        @return string  Created link type; None no link was created
        """

        if _bForce: _bBatch = True

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # GIT link
            sLink = self._link(sFileGIT, sFileActual, _sLink, _bBatch, _bForce)
            if sLink is not None:
                self._INFO('File successfully linked to its GIT sibling; %s (%s)' % (_sFileActual, sLink))
            return sLink

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to link file to its GIT sibling')


    def _gitCommand(self, _lArguments, _bRedirectStdOut=True):
        """
        Execute the GIT command with the given arguments, within the GIT sub-repository.

        @param  list  _lArguments       GIT command arguments
        @param  bool  _bRedirectStdOut  Redirect standard output

        @return string  Resulting standard output (if redirected)
        """

        # Execute shell command
        lCommand = ['git']+_lArguments
        return self._shellCommand(lCommand, self.__asSubRepositories['git'], _bRedirectStdOut)


    def _saveFileOriginal(self, _sFileOriginal, _sFileSource, _bBatch=False, _bForce=False):
        """
        Save the given original file.

        @param  string  _sFileOriginal  File (canonical path) within original files sub-repository
        @param  string  _sFileSource    Original file source (path)
        @param  bool    _bBatch         Batch mode (no confirmation prompts)
        @param  bool    _bForce         Forced batch mode
        """

        # Update original files sub-repository
        self._DEBUG('Copying original file; %s => %s' % (_sFileSource, _sFileOriginal))
        self.mkdir(self._dirpath(_sFileOriginal))
        self._cp(_sFileSource, _sFileOriginal)


    def saveFileOriginal(self, _sFileActual, _sFileSource, _bBatch=False, _bForce=False):
        """
        Save the given original file.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  string  _sFileSource  Original file source (path)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode
        """

        if _bForce: _bBatch = True

        try:
            # Paths
            sFileOriginal = self.getRepositoryPath('original', _sFileActual)

            # Confirmation
            if os.path.exists(sFileOriginal):
                if not _bBatch:
                    if self._confirm('Update original file', ['y','n'], 'y')!='y':
                        return
                elif not _bForce:
                    raise EnvironmentError(errno.EPERM, 'Cannot update original file (unless forced)')

            # Save original file
            self._saveFileOriginal(sFileOriginal, _sFileSource, _bBatch, _bForce)
            self._INFO('Original file successfully saved; %s' % _sFileActual)
        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed save original file')


    def _saveFileGIT(self, _sFileGIT, _sFileActual, _sLink=None, _bBatch=False, _bForce=False):
        """
        Save the given GIT file.

        @param  string  _sFileGIT     File (canonical path) within GIT sub-repository
        @param  string  _sFileActual  Actual file (canonical path)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode
        """

        # Update GIT sub-repository
        self._link(_sFileGIT, _sFileActual, _sLink, _bBatch, _bForce)
        self._DEBUG('GIT add file; %s' % _sFileGIT)
        self._gitCommand(['add', _sFileGIT])


    def saveFileGIT(self, _sFileActual, _sLink=None, _bBatch=False, _bForce=False):
        """
        Save the given GIT file.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode
        """

        if _bForce: _bBatch = True

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Confirmation
            if os.path.exists(sFileGIT):
                if not _bBatch:
                    if self._confirm('Update GIT file', ['y','n'], 'y')!='y':
                        return
                elif not _bForce:
                    raise EnvironmentError(errno.EPERM, 'Cannot update GIT file (unless forced)')

            # Save GIT file
            self._saveFileGIT(sFileGIT, sFileActual, _sLink, _bBatch, _bForce)
            self._INFO('GIT file successfully saved; %s' % _sFileActual)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed save GIT file')

    #
    # API (commands)
    #

    def _check(self, _bInitialize=False, _bBatch=False):
        """
        Check/initialize the configuration repository (and various sub-repositories).

        @param  bool  _bInitialize  Initialize mode (create/fix configuration repository)
        @param  bool  _bBatch       Batch mode (no confirmation prompts)
        """

        # Paths
        sPath = self.__sRoot = self.getCanonicalPath(self.__sRoot, True)
        self.__asSubRepositories = {
            'root': sPath,
            'git': os.path.join(sPath, 'git'),
            'original': os.path.join(sPath, 'original'),
            'flag': os.path.join(sPath, 'flag'),
            'pkglist': os.path.join(sPath, 'pkglist')
        }

        # Check sub-directories
        for sRepository in ('git', 'original', 'flag'):
            sPath = self.__asSubRepositories[sRepository]
            self._DEBUG('Checking sub-repository directory; %s' % sPath)
            if not os.path.exists(sPath):
                if _bInitialize:
                    self._DEBUG('Creating sub-repository directory; %s' % sPath)
                    os.mkdir(sPath)
                    # ... placeholder (prevent recursive deletion)
                    if sRepository!='git':
                        sPlaceholder = os.path.join(sPath, '.placeholder')
                        with open(sPlaceholder, 'w') as fPlaceholder:
                            os.chmod(sPlaceholder, 0444)
                else:
                    raise EnvironmentError(errno.ENOENT, 'Sub-repository directory is missing')
            if not os.path.isdir(sPath):
                raise EnvironmentError(errno.ENOTDIR, 'Existing path is not a directory')
            if not os.access(sPath, os.W_OK|os.X_OK):
                raise EnvironmentError(errno.EACCES, 'Cannot write to directory')

        # GIT repository
        sPath = os.path.join(self.__asSubRepositories['git'], '.git')
        self._DEBUG('Checking GIT; %s' % sPath)
        if not os.path.exists(sPath):
            if _bInitialize:
                self._DEBUG('Initializing GIT; %s' % sPath)
                self._gitCommand(['init'])
            else:
                raise EnvironmentError(errno.ENOENT, 'GIT is not initialized')
        if not os.path.isdir(sPath):
            raise EnvironmentError(errno.ENOTDIR, 'Existing path is not a directory')
        if not os.access(sPath, os.W_OK|os.X_OK):
            raise EnvironmentError(errno.EACCES, 'Cannot write to directory')

        # Packages listing
        sPath = self.__asSubRepositories['pkglist']
        self._DEBUG('Checking packages listing file; %s' % sPath)
        if not os.path.exists(sPath):
            if _bInitialize:
                self._DEBUG('Creating packages listing file; %s' % sPath)
                self._pkglist(sPath)
                self._add(sPath, sPath, _bBatch=True)
            else:
                raise EnvironmentError(errno.ENOENT, 'Packages listing file is missing')
        if not os.path.isfile(sPath):
            raise EnvironmentError(errno.ENOENT, 'Existing path is not a file')
        if not os.access(sPath, os.W_OK):
            raise EnvironmentError(errno.EACCES, 'Cannot write to file')


    def check(self, _bInitialize=False, _bBatch=False):
        """
        Check/initialize the configuration repository (and various sub-repositories).
        Returns bool False if processing shall be interrupted following user interaction.
        This method MUST be called before any other command is attempted.
        (including validation, informational messages and exceptions handling)

        @param  bool  _bInitialize  Initialize mode (create/fix configuration repository)
        @param  bool  _bBatch       Batch mode (no confirmation prompts)

        @return bool  OK to proceed
        """

        sPath = self.__sRoot
        try:

            # Check root existency
            if not os.path.exists(sPath):
                if _bInitialize:
                    if not _bBatch:
                        if self._confirm('Create repository directory; %s' % sPath, ['y','n'], 'y')!='y':
                            return False
                    self._mkdir(sPath)
                else:
                    raise EnvironmentError(errno.ENOENT, 'Invalid configuration repository')

            # Check repository
            self._check(_bInitialize, _bBatch)
            if _bInitialize:
                self._INFO('Configuration repository successfully initialized; %s' % sPath)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, sPath))
            raise EnvironmentError(e.errno, 'Failed to check/initialize repository')

        return True


    def _verify(self, _sFileActual=None, _sLink=None, _bBatch=False, _bForce=False):
        """
        Verify the given file (or all files if ommitted) are correctly linked.

        @param  string  _sFileActual  Actual file (canonical path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode
        """

        # Verify one particular file
        if _sFileActual is not None:
            self.link(_sFileActual, _sLink, _bBatch, _bForce)

        # Verify all files
        else:
            for sFileActual in sorted(self._list()):
                self.link(sFileActual, None, _bBatch, _bForce)


    def verify(self, _sFileActual=None, _sLink=None, _bBatch=False, _bForce=False):
        """
        Verify the given file (or all files if ommitted) are correctly linked.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode
        """

        if _bForce: _bBatch = True

        try:

            # Paths
            sFileActual = None
            if _sFileActual is not None:
                sFileActual = self.getCanonicalPath(_sFileActual)
                sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if _sFileActual is not None and not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Verify
            self._verify(sFileActual, _sLink, _bBatch, _bForce)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to verify configuration repository consistency')


    def _list(self, _sFlag=None):
        """
        Return the list of files in the configuration repository,
        along all flags (flag=@FLAGS) or matching any given flag.

        @param  string   _sFlag  File flag to match (or @FLAGS to display all flags)

        @return dict|list  Dictionnary associating files to their corresponding (list of) flags
        """

        # Handle flags
        dlFiles = None
        dlFiles_flags = None
        dsFiles_git = None
        if _sFlag is not None:
            if _sFlag=='@FLAGS' or _sFlag[:5]=='@GIT:':
                # Retrieve files GIT status
                self._DEBUG('Retrieving files GIT status')
                sFiles_git = self._shellCommand(['git', 'status', '--porcelain'], self.__asSubRepositories['git'])
                # ... flags
                dsFiles_git = {}
                for sGIT in sFiles_git.splitlines():
                    sFileActual = '/%s' % sGIT[3:]
                    dsFiles_git[sFileActual] = '@GIT:%s' % sGIT[:2].replace(' ', '_')

            if _sFlag[:5]=='@GIT:':
                # Match GIT flags
                self._DEBUG('Matching files GIT status; %s' % _sFlag)
                lFiles = self._shellCommand(['find', '.', '-type', 'f', '-not', '-path', './.git/*'], self.__asSubRepositories['git']).splitlines()
                lFiles = map(lambda s:s.lstrip('.'), lFiles)
                dlFiles = {}
                for sFileActual in lFiles:
                    if sFileActual in dsFiles_git:
                        if _sFlag==dsFiles_git[sFileActual]:
                            dlFiles[sFileActual] = None
                    else:
                        if _sFlag=='@GIT:__':
                            dlFiles[sFileActual] = None

            elif _sFlag=='@FLAGS':
                # Retrieve files flags
                sRepositoryFlag = self.__asSubRepositories['flag']
                self._DEBUG('Retrieving files flags')
                lFiles = self._shellCommand(['find', '.', '-type', 'f', '-not', '-name', '.placeholder'], sRepositoryFlag).splitlines()
                # ... flags
                dlFiles_flags = {}
                for sFileFlag in lFiles:
                    sFileActual = sFileFlag.lstrip('.')
                    with open(os.path.join(sRepositoryFlag, sFileFlag), 'r') as fFileFlag:
                        dlFiles_flags[sFileActual] = sorted(fFileFlag.read().splitlines())
            else:
                # Find all files matching flag
                self._DEBUG('Matching files flags; %s' % _sFlag)
                lFiles = self._shellCommand(['find', '.', '-type', 'f', '-not', '-name', '.placeholder', '-exec', 'grep', '-q', '^%s$' % _sFlag, '{}', ';', '-print'], self.__asSubRepositories['flag']).splitlines()
                dlFiles = dict.fromkeys(map(lambda s:s.lstrip('.'), lFiles))

        # List
        if dlFiles is None:
            # Retrieve list of all GIT files
            self._DEBUG('Retrieving GIT files list')
            lFiles = self._shellCommand(['find', '.', '-type', 'f', '-not', '-path', './.git/*'], self.__asSubRepositories['git']).splitlines()
            dlFiles = dict.fromkeys(map(lambda s:s.lstrip('.'), lFiles))

        # Add flags
        if _sFlag=='@FLAGS':
            self._DEBUG('Adding flags')
            for sFileActual in dlFiles:
                dlFiles[sFileActual] = []
                if sFileActual in dlFiles_flags:
                    dlFiles[sFileActual] += dlFiles_flags[sFileActual]
                if sFileActual in dsFiles_git:
                    dlFiles[sFileActual] += [dsFiles_git[sFileActual]]
                else:
                    dlFiles[sFileActual] += ['@GIT:__']

        # Done
        return dlFiles


    def list(self, _sFlag=None):
        """
        Return the list of files in the configuration repository,
        along all flags (flag=@FLAGS) or matching any given flag.
        (including exceptions handling)

        @param  string   _sFlag  File flag to match (or @FLAGS to display all flags)

        @return dict|list  Dictionnary associating files to their corresponding (list of) flags
        """

        try:

            # List files
            return self._list(_sFlag)

        except EnvironmentError as e:
            self._ERROR(e.strerror)
            raise EnvironmentError(e.errno, 'Failed to list files in the configuration repository')


    def _add(self, _sFileActual, _sFileOriginal=None, _sLink=None, _bBatch=False, _bForce=False):
        """
        Add the given file to the configuration respository.
        If it already exists, or if an (alternate) original file is specified,
        it may also be added to the original files sub-repository.

        @param  string  _sFileActual    Actual file (canonical path)
        @param  string  _sFileOriginal  Original file (path)
        @param  string  _sLink          Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch         Batch mode (no confirmation prompts)
        @param  bool    _bForce         Forced batch mode

        @return bool  True if the file was actually added
        """

        # Paths
        sFileGIT = self._getRepositoryPath('git', _sFileActual)

        # Original file
        if _sFileOriginal is not None:
            self.saveFileOriginal(_sFileActual, _sFileOriginal, _bBatch)

        # GIT file
        self.saveFileGIT(_sFileActual, _sLink, _bBatch)

        # Done
        return True


    def add(self, _sFileActual, _sbFileOriginal=None, _sLink=None, _bBatch=False, _bForce=False):
        """
        Add or create the given file to the GIT sub-repository.
        If it already exists, or if an alternate original file is specified,
        it will be added to the original files sub-repository.
        (including validation, informational messages and exceptions handling)

        @param  string       _sFileActual     Actual file (path)
        @param  string|bool  _sbFileOriginal  Original file (path); or, if True, use the actual file as original (or don't if False)
        @param  string       _sLink           Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool         _bBatch          Batch mode (no confirmation prompts)
        @param  bool         _bForce          Forced batch mode

        @return bool  True if the file was actually added
        """

        if _bForce: _bBatch = True
        if isinstance(_sbFileOriginal, bool):
            if _sbFileOriginal:
                _sbFileOriginal = _sFileActual
            else:
                _sbFileOriginal = None

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)
            sFileOriginal = self._getRepositoryPath('original', sFileActual)

            # Check
            if os.path.exists(sFileGIT) and not _bForce:
                return False
            if os.path.exists(sFileActual):
                if not os.path.isfile(sFileActual):
                    raise EnvironmentError(errno.EINVAL, 'Invalid file')
                try:
                    os.stat(sFileActual)
                except EnvironmentError as e:
                    raise EnvironmentError(e.errno, 'Unreadable file')
                if _sbFileOriginal is not None:
                    try:
                        os.stat(_sbFileOriginal)
                    except EnvironmentError as e:
                        raise EnvironmentError(e.errno, 'Missing or unreadable original file')

            # Original file
            sFileOriginal_source = None
            if _sbFileOriginal is not None:
                sFileOriginal_source = _sbFileOriginal
            elif os.path.exists(_sFileActual):
                    if not _bBatch:
                        if os.path.exists(sFileOriginal):
                            sDefaultChoice = 'n'
                        else:
                            sDefaultChoice = 'y'
                        if self._confirm('Save original file', ['y','n'], sDefaultChoice)=='y':
                            sFileOriginal_source = _sFileActual

            # Add file
            bAdded = self._add(sFileActual, sFileOriginal_source, _sLink, _bBatch, _bForce)
            if bAdded:
                self._INFO('File successfully added to configuration repository; %s' % _sFileActual)
            return bAdded

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to add file to configuration repository')


    def _copy(self, _sFileActual, _sFileSource, _sLink=None, _bBatch=False, _bForce=False):
        """
        Add the given file to the configuration respository, copying the specified source file.

        @param  string  _sFileActual  Actual file (canonical path)
        @param  string  _sFileSource  Source file (path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode

        @return bool  True if the file was actually copied
        """

        # Check existency
        bFileActualExists = os.path.exists(_sFileActual)
        if bFileActualExists:
            # Add (already existing) file to repository
            if not _bBatch:
                self.add(_sFileActual, None, _sLink, False)
            else:
                # Force saving of unexisting original file (better safe than sorry)
                sFileOriginal = self._getRepositoryPath('original', _sFileActual)
                self.add(_sFileActual, not os.path.exists(sFileOriginal), _sLink, True)

            # @EDITED ?
            if self._flagged(_sFileActual, '@EDITED'):
                if not _bForce:
                    raise EnvironmentError(errno.EPERM, 'Cannot overwrite @EDITED file (unless forced)')
                else:
                    self._unflag(_sFileActual, '@EDITED')

        # Copy file
        self._cp(_sFileSource, _sFileActual)

        # Add (previously not existing) file to repository
        if not bFileActualExists:
            self.add(_sFileActual, False, _sLink, True)

        # Done
        return True


    def copy(self, _sFileActual, _sFileSource, _sLink=None, _bBatch=False, _bForce=False):
        """
        Add the given file to the configuration respository, copying the specified source file.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  string  _sFileSource  Source file (path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode

        @return bool  True if the file was actually copied
        """

        if _bForce: _bBatch = True

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)

            # Confirmation
            if os.path.exists(sFileActual):
                if not _bBatch:
                    if self._confirm('Overwrite existing file', ['y','n'])!='y':
                        return

            # Copy file
            bCopied = self._copy(sFileActual, _sFileSource, _sLink, _bBatch, _bForce)
            if bCopied:
                self._INFO('File successfully copied; %s -> %s' % (_sFileSource, _sFileActual))

            # Better verify the file consistency
            if bCopied:
                self.verify(_sFileActual, _sLink, True, True)

            # Done
            return bCopied

        except EnvironmentError as e:
            self._ERROR('%s; %s X> %s' % (e.strerror, _sFileSource, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to copy file')


    def _move(self, _sFileActual, _sFileDestination, _sLink=None, _bBatch=False, _bForce=False):
        """
        Move the given file to the given destination.

        @param  string  _sFileActual       Actual file (canonical path)
        @param  string  _sFileDestination  Destination file (canonical path)
        @param  string  _sLink             Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch            Batch mode (no confirmation prompts)
        @param  bool    _bForce            Forced batch mode

        @return bool  True if the file was actually moved
        """

        # Paths
        # ...source
        sFileGIT_src = self._getRepositoryPath('git', _sFileActual)
        sFileOriginal_src = self._getRepositoryPath('original', _sFileActual)
        sFileFlag_src = self._getRepositoryPath('flag', _sFileActual)
        # ...destination
        sFileGIT_dst = self._getRepositoryPath('git', _sFileDestination)
        sFileOriginal_dst = self._getRepositoryPath('original', _sFileDestination)
        sFileFlag_dst = self._getRepositoryPath('flag', _sFileDestination)

        # Link
        (bLinked, sLink) = self._isLinked(sFileGIT_src, _sFileActual)
        if not bLinked:
            raise EnvironmentError(errno.EAGAIN, 'Source file is inconsistent')
        if _sLink is not None:
            sLink = _sLink

        # Copy actual file (and save its original)
        self._DEBUG('Copying GIT file; %s -> %s' % (_sFileActual, _sFileDestination))
        if not self.copy(_sFileDestination, _sFileActual, _sLink, _bBatch, _bForce):
            return False

        # Copy flags file
        if os.path.exists(sFileFlag_src):
            self._DEBUG('Copying flags file; %s -> %s' % (sFileFlag_src, sFileFlag_dst))
            self.mkdir(self._dirpath(sFileFlag_dst))
            self._cp(sFileFlag_src, sFileFlag_dst)

        # Source original file
        if os.path.exists(sFileOriginal_src):
            if not _bBatch:
                if self._confirm('Overwrite destination original with source original file', ['y','n'])=='y':
                    self._DEBUG('Moving source original file to destination original file; %s -> %s' % (sFileOriginal_src, sFileOriginal_dst))
                    self.saveFileOriginal(_sFileDestination, sFileOriginal_src, True, True)
                    self._rm(sFileOriginal_src)
                elif self._confirm('Delete source original file (it will not be restored)', ['y','n'])=='y':
                    self._DEBUG('Removing source original file; %s' % sFileOriginal_src)
                    self._rm(sFileOriginal_src)

        # Purge source file
        self._DEBUG('Removing source file; %s' % _sFileActual)
        self.remove(_sFileActual, True, True)

        # Done
        return True


    def move(self, _sFileActual, _sFileDestination, _sLink=None, _bBatch=False, _bForce=False):
        """
        Move the given file to the given destination.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual       Actual file (path)
        @param  string  _sFileDestination  Destination file (path)
        @param  string  _sLink             Link type (among: 'hardlink', 'symlink', 'copy' or None)
        @param  bool    _bBatch            Batch mode (no confirmation prompts)
        @param  bool    _bForce            Forced batch mode

        @return bool  True if the file was actually moved
        """

        if _bForce: _bBatch = True

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileDestination = self.getCanonicalPath(_sFileDestination)
            sFileGIT_src = self._getRepositoryPath('git', sFileActual)
            sFileGIT_dst = self._getRepositoryPath('git', sFileDestination)

            # Check
            if not os.path.exists(sFileGIT_src):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')
            if os.path.exists(sFileGIT_dst):
                raise EnvironmentError(errno.EEXIST, 'Destination file exists (please "remove")')
            if not self.isLinked(_sFileActual)[0]:
                raise EnvironmentError(errno.EAGAIN, 'Inconsistent consiguration repository (please "verify")')

            # Move file
            bMoved = self._move(sFileActual, sFileDestination, _sLink, _bBatch, _bForce)
            if bMoved:
                self._INFO('File successfully moved; %s' % _sFileActual)
            return bMoved

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to move file')


    def _remove(self, _sFileActual, _bBatch=False, _bForce=False):
        """
        Remove the given file from the configuration respository.

        @param  string  _sFileActual  Actual file (canonical path)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode

        @return bool  True if the file was actually removed
        """

        # Paths
        sFileGIT = self._getRepositoryPath('git', _sFileActual)
        sFileOriginal = self._getRepositoryPath('original', _sFileActual)
        sFileFlag = self._getRepositoryPath('flag', _sFileActual)

        # Remove GIT file
        self._DEBUG('Removing GIT file and parent directory; %s' % sFileGIT)
        if os.path.exists(sFileGIT):
            try:
                self._gitCommand(['rm', '--force', sFileGIT])
            except EnvironmentError as e:
                # NOTE: 'git rm' will fail on untracked file
                self._WARNING('Failed to GIT-remove file; %s (%s)' % (_sFileActual, e.strerror))
                if os.path.exists(sFileGIT):
                    self._rm(sFileGIT)
        self.rmdir(os.path.dirname(sFileGIT))

        # Remove file flags
        self._DEBUG('Removing flags file and parent directory; %s' % sFileFlag)
        if os.path.exists(sFileFlag):
            self._rm(sFileFlag)
        self.rmdir(os.path.dirname(sFileFlag))

        # Remove actual file
        self._DEBUG('Removing file; %s' % _sFileActual)
        if os.path.exists(_sFileActual) or os.path.islink(_sFileActual):
            self._rm(_sFileActual)

        # Restore and remove original file
        self._DEBUG('Restoring original file and removing parent directory; %s' % sFileOriginal)
        if os.path.exists(sFileOriginal):
            self._mv(sFileOriginal, _sFileActual)
        self.rmdir(os.path.dirname(sFileOriginal))

        # Done
        return True


    def remove(self, _sFileActual, _bBatch=False, _bForce=False):
        """
        Remove the given file from the configuration respository.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  bool    _bBatch       Batch mode (no confirmation prompts)
        @param  bool    _bForce       Forced batch mode

        @return bool  True if the file was actually removed
        """

        if _bForce: _bBatch = True

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not _bForce and not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Confirmation
            if os.path.exists(sFileGIT):
                bEdited = self._flagged(sFileActual, '@EDITED')
                if not _bBatch:
                    if not os.path.exists(sFileGIT):
                        raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')
                    if bEdited:
                        sPrompt = 'Remove @EDITED file from configuration repository'
                    else:
                        sPrompt = 'Remove file from configuration repository'
                    if self._confirm(sPrompt, ['y','n'])!='y':
                        return False
                elif not _bForce:
                    if not os.path.exists(sFileGIT):
                        return False
                    if bEdited:
                        raise EnvironmentError(errno.EPERM, 'Cannot remove @EDITED file (unless forced)')

            # Remove file
            bRemoved = self._remove(sFileActual, _bBatch, _bForce)
            if bRemoved:
                if os.path.exists(sFileActual):
                    self._INFO('Original file successfully restored; %s' % _sFileActual)
                else:
                    self._INFO('File successfully removed; %s' % _sFileActual)
            return bRemoved

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to remove file')


    def _edit(self, _sFileActual, _sLink=None):
        """
        Edit the given file (adds it to the GIT sub-repository if needs be).
        The file will be flagged as '@EDITED' if modified.

        @param  string  _sFileActual  Actual file (canonical path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)

        @return bool  True if the file was actually edited
        """

        # Edit
        oStat_before = os.stat(_sFileActual)
        sEditor = os.getenv('EDITOR', 'vi');
        self._shellCommand([sEditor, _sFileActual], None, False)
        oStat_after = os.stat(_sFileActual)

        # Edited ?
        if oStat_before.st_mtime!=oStat_after.st_mtime:
            self._flag(_sFileActual, '@EDITED')
            return True
        return False


    def edit(self, _sFileActual, _sLink=None):
        """
        Edit the given file (adds it to the GIT sub-repository if needs be).
        The file will be flagged as '@EDITED' if modified.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  string  _sLink        Link type (among: 'hardlink', 'symlink', 'copy' or None)

        @return bool  True if the file was actually removed
        """

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not os.path.exists(sFileGIT):
                if self._confirm('Add file to configuration repository', ['y','n'], 'y')!='y':
                    return False
                if not self.add(sFileActual):
                    return False

            # Edit file
            return self._edit(sFileActual, _sLink)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to edit file')


    def _permissions(self, _sFileActual, _sMode=None, _sOwner=None):
        """
        Change/return the permissions of the given file.

        @param  string   _sFileActual  Actual file (canonical path)
        @param  string   _sMode        Mode string (chmod-like)
        @param  string   _sOwner       Owner string (chown-like)

        @return set(int,int,int)  File permissions: mode, owner (uid) and group (gid)
        """

        # Paths
        sFileGIT = self._getRepositoryPath('git', _sFileActual)

        # Change mode
        if _sMode is not None:
            self._shellCommand(['chmod', _sMode, sFileGIT])
            self._shellCommand(['chmod', _sMode, _sFileActual])

        # Change owner
        if _sOwner is not None:
            self._shellCommand(['chown', _sOwner, sFileGIT])
            self._shellCommand(['chown', _sOwner, _sFileActual])

        # Retrieve
        oStat = os.stat(sFileGIT)
        return (oStat.st_mode, oStat.st_uid, oStat.st_gid)


    def permissions(self, _sFileActual, _sMode=None, _sOwner=None):
        """
        Change/return the permissions of the given file.
        (including validation, informational messages and exceptions handling)

        @param  string   _sFileActual  Actual file (path)
        @param  string   _sMode        Mode string (chmod-like)
        @param  string   _sOwner       Owner string (chown-like)

        @return set(int,int,int)  File permissions: mode, owner (uid) and group (gid)
        """

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Check
            if _sMode is not None and not _sMode.strip():
                _sMode = None
            if _sOwner is not None and not _sOwner.strip():
                _sOwner = None

            # Permissions
            return self._permissions(sFileActual, _sMode, _sOwner)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to change/retrieve file permissions')


    def _flag(self, _sFileActual, _sFlag):
        """
        Add the given flag to the given file.

        @param  string   _sFileActual  Actual file (canonical path)
        @param  string   _sFlag        File flag
        """

        # Paths
        sFileFlag = self._getRepositoryPath('flag', _sFileActual)

        # Check
        if not os.path.exists(sFileFlag):
            sDirFlag = self._dirpath(sFileFlag)
            if not os.path.exists(sDirFlag):
                self._mkdir(sDirFlag)

        # Flag
        lFlags = []
        if os.path.exists(sFileFlag):
            self._DEBUG('Reading flag file; %s' % sFileFlag)
            with open(sFileFlag, 'r') as fFileFlag:
                lFlags = fFileFlag.read().splitlines()
        lFlags += [_sFlag]
        lFlags = sorted(set(lFlags))
        self._DEBUG('Writing flag file; %s' % sFileFlag)
        with open(sFileFlag, 'w') as fFileFlag:
            fFileFlag.write('\n'.join(lFlags))


    def flag(self, _sFileActual, _sFlag):
        """
        Add the given flag to the given file.
        (including validation, informational messages and exceptions handling)

        @param  string   _sFileActual  Actual file (path)
        @param  string   _sFlag        File flag
        """

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Check flag
            if any((c not in '_-abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ01234567890') for c in _sFlag):
                raise EnvironmentError(errno.EINVAL, 'Invalid flag')

            # Add flag
            self._flag(sFileActual, _sFlag)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to add flag to file')


    def _unflag(self, _sFileActual, _sFlag):
        """
        Remove the given flag from the given file.

        @param  string   _sFileActual  Actual file (canonical path)
        @param  string   _sFlag        File flag
        """

        # Paths
        sFileFlag = self._getRepositoryPath('flag', _sFileActual)

        # Check
        if not os.path.exists(sFileFlag):
            return

        # Flag
        self._DEBUG('Reading flags file; %s' % sFileFlag)
        with open(sFileFlag, 'r') as fFileFlag:
            lFlags = fFileFlag.read().splitlines()
        lFlags = sorted(set(lFlags))
        lFlags.remove(_sFlag)
        if lFlags:
            self._DEBUG('Writing flags file; %s' % sFileFlag)
            with open(sFileFlag, 'w') as fFileFlag:
                fFileFlag.write('\n'.join(lFlags))
        else:
            self._DEBUG('Removing empty flags file; %s' % sFileFlag)
            self._rm(sFileFlag)
            self._rmdir(os.path.dirname(sFileFlag))


    def unflag(self, _sFileActual, _sFlag):
        """
        Remove the given flag from the given file.
        (including validation, informational messages and exceptions handling)

        @param  string   _sFileActual  Actual file (path)
        @param  string   _sFlag        File flag
        """

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Remove flag
            self._unflag(sFileActual, _sFlag)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to remove flag from file')


    def _flagged(self, _sFileActual, _sFlag=None):
        """
        Test the given flag for the given file or
        list all associated flags if no flag is specified.

        @param  string  _sFileActual  Actual file (canonical path)
        @param  string  _sFlag        File flag

        @return bool|list  True if flag matches, False otherwise or flags list if no flag is given
        """

        # Paths
        sFileFlag = self._getRepositoryPath('flag', _sFileActual)

        # Check
        if not os.path.exists(sFileFlag):
            if _sFlag is not None:
                return False
            return []

        # Flag
        self._DEBUG('Reading flag file; %s' % sFileFlag)
        with open(sFileFlag, 'r') as fFileFlag:
            lFlags = fFileFlag.read().splitlines()
        if _sFlag is not None:
            if _sFlag in lFlags: return True
            return False
        return lFlags


    def flagged(self, _sFileActual, _sFlag):
        """
        Test the given flag for the given file or
        list all associated flags if no flag is specified.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual  Actual file (path)
        @param  string  _sFlag        File flag

        @return bool|list  True if flag matches, False otherwise or flags list if no flag is given
        """

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Remove flag
            return self._flagged(sFileActual, _sFlag)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to retrieve flags for file')


    def _original(self, _sFileActual):
        """
        Return the original content of the given file.

        @param  string   _sFileActual  Actual file (canonical path)

        @return string  File original content
        """

        # Paths
        sFileOriginal = self._getRepositoryPath('original', _sFileActual)

        # Check
        if not os.path.exists(sFileOriginal):
            return ''

        # Original
        self._DEBUG('Reading original file; %s' % sFileOriginal)
        with open(sFileOriginal, 'r') as fFileOriginal:
            sOriginal = fFileOriginal.read()
        return sOriginal


    def original(self, _sFileActual):
        """
        Return the original content of the given file.
        (including validation, informational messages and exceptions handling)

        @param  string   _sFileActual  Actual file (path)

        @return string  File original content
        """

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Show original file
            return self._original(sFileActual)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to retrieve the file original content')


    def _delta(self, _sFileActual, _sCommentPrefix=None, _bRedirectStdOut=True):
        """
        Return the difference (diff -uN) between the given file and its original content.
        If a comment prefix is given, commented and empty lines will be stripped off from the result.

        @param  string  _sFileActual      Actual file (canonical path)
        @param  string  _sCommentPrefix   Comment prefix
        @param  bool    _bRedirectStdOut  Redirect standard output

        @return string  Differences (diff -uN) output (if redirected)
        """

        # Paths
        sFileOriginal = self._getRepositoryPath('original', _sFileActual)

        # Differences
        if _sCommentPrefix is None:
            sDifferences = self._shellCommand(['diff', '-uN', '--label', 'ORIGINAL', sFileOriginal, _sFileActual], None, _bRedirectStdOut, True)
        else:
            with tempfile.NamedTemporaryFile() as fFileOriginal_tmp:
                with tempfile.NamedTemporaryFile() as fFileActual_tmp:
                    sCommentRexExp = '^[[:space:]]*(%s|$)' % re.escape(_sCommentPrefix)
                    fFileOriginal_tmp.write(self._shellCommand(['grep', '-Ev', sCommentRexExp, sFileOriginal], None, True, True))
                    fFileActual_tmp.write(self._shellCommand(['grep', '-Ev', sCommentRexExp, _sFileActual], None, True, True))
                    fFileOriginal_tmp.flush()
                    fFileActual_tmp.flush()
                    sDifferences = self._shellCommand(['diff', '-uN', '--label', 'ORIGINAL', '--label', _sFileActual, fFileOriginal_tmp.name, fFileActual_tmp.name], None, _bRedirectStdOut, True)
        return sDifferences


    def delta(self, _sFileActual, _sCommentPrefix=None, _bRedirectStdOut=True):
        """
        Return the difference (diff -uN) between the given file and its original content.
        If a comment prefix is given, commented and empty lines will be stripped off from the result.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFileActual      Actual file (path)
        @param  string  _sCommentPrefix   Comment prefix
        @param  bool    _bRedirectStdOut  Redirect standard output

        @return string  Differences (diff -uN) output (if redirected)
        """

        try:

            # Paths
            sFileActual = self.getCanonicalPath(_sFileActual)
            sFileGIT = self._getRepositoryPath('git', sFileActual)

            # Check
            if not os.path.exists(sFileGIT):
                raise EnvironmentError(errno.ENOENT, 'No such file (in configuration repository)')

            # Remove flag
            return self._delta(sFileActual, _sCommentPrefix, _bRedirectStdOut)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFileActual))
            raise EnvironmentError(e.errno, 'Failed to retrieve the file differences')


    def _pkglist(self, _sPath=None):
        """
        Return (or saves) the list of (manually installed) packages.

        @param  string   _sPath  File to save the packages listing to

        @return string  Packages listing (if not path is specified)
        """

        # Execute shell command
        lCommand = ['aptitude', 'search', '--disable-columns', '--display-format', '%p', '--sort', 'name', '?and(?installed,?not(?automatic))']
        sStdOut = self._shellCommand(lCommand)

        # Save packages listing file
        if _sPath is not None:
            self._DEBUG('Saving packages listing file; %s' % _sPath)
            fPackageListing = open(_sPath, 'w')
            fPackageListing.write(sStdOut)
            fPackageListing.close()
            return None
        else:
            return sStdOut

    def pkglist(self, _sPath=None):
        """
        Return (or save) the list of (manually installed) packages.
        (including validation, informational messages and exceptions handling)

        @param  string   _sPath  File to save the packages listing to

        @return string  Packages listing (if not path is specified)
        """

        try:

            # Save packages listing file
            return self._pkglist(_sPath)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sPath))
            raise EnvironmentError(e.errno, 'Failed to retrieve/save packages listing file')

    def _git(self, _sCommand, _lArguments, _bRedirectStdOut=True):
        """
        Execute the given GIT command for the given file.

        @param  string  _sCommand         GIT (sub-)command
        @param  string  _lArguments       Additional arguments
        @param  bool    _bRedirectStdOut  Redirect standard output

        @return string  GIT command standard output (if redirected)
        """

        # Arguments
        if _sCommand=='commit':
            if '--author' not in _lArguments:
                _lArguments += ['--author', '%s <%s>' % (self.__sAuthor, self.__sEmail)]

        # Execute the GIT command
        return self._gitCommand([_sCommand]+_lArguments, _bRedirectStdOut)


    def git(self, _lArguments, _bRedirectStdOut=True):
        """
        Execute 'git' with the given arguments.
        The GIT (sub-)command MUST be the first argument.
        (including validation, informational messages and exceptions handling)

        @param  string  _lArguments       GIT command arguments
        @param  bool    _bRedirectStdOut  Redirect standard output

        @return string  GIT command standard output (if redirected)
        """

        try:

            # Verify repository
            self.verify(_bBatch=_bRedirectStdOut)

            # Parse command line
            lArguments = []
            sCommand = None
            for s in _lArguments:
                if s[0]!='-':
                    if sCommand is None:
                        sCommand = s
                        continue
                lArguments += [s]

            # GIT command
            return self._git(sCommand, lArguments, _bRedirectStdOut)

        except EnvironmentError as e:
            self._ERROR(e.strerror)
            raise EnvironmentError(e.errno, 'Failed to execute GIT command')

    def _a2ps(self, _sFilePostscript, _sFlag=None, _bBatch=False, _bForce=False):
        """
        Create a Postscript document with all (text) files in the configuration repository.

        @param  string  _sFilePostscript  Postcript file (path)
        @param  string  _sFlag            File flag to match
        @param  bool    _bBatch           Batch mode (no confirmation prompts)
        @param  bool    _bForce           Forced batch mode
        """

        # Retrieve the files list, along their type
        self._DEBUG('Retrieving GIT files list')
        oPopen = subprocess.Popen(
            ['find', '.', '-type', 'f', '-not', '-path', './.git/*', '-print0'],
            cwd=self._getRepositoryPath('git'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        oPopen_sub = subprocess.Popen(
            ['xargs', '-0', 'file', '-N'],
            cwd=self._getRepositoryPath('git'),
            stdin=oPopen.stdout,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        oPopen.stdout.close()
        (sStdOut, sStdErr) = oPopen_sub.communicate()
        if oPopen_sub.returncode!=0:
            raise EnvironmentError(oPopen_sub.returncode, sStdErr)
        dlFiles = {}
        for sLine in sStdOut.splitlines():
            iSeparator = sLine.rfind(':')
            dlFiles[sLine[:iSeparator].lstrip('.')] = sLine[iSeparator+1:].strip()

        # Filter non-text files out
        self._DEBUG('Filtering (text) files; flag=%s' % _sFlag)
        lFiles = []
        for sFile, sType in dlFiles.iteritems():
            if self.__reFileText.search(sType) is None:
                continue
            if _sFlag is not None and not self._flagged(sFile, _sFlag):
                continue
            lFiles += [sFile]

        # Execute A2PS command
        if lFiles:
            self._DEBUG('Creating Postscript file; %s' % _sFilePostscript)
            self._shellCommand(['a2ps', '--medium=A4', '--portrait', '--columns=1', '--borders=on', '--no-header', '--toc', '--left-title=$f', '--right-title=$p./$p#', '--left-footer=%M - %D{%Y.%m.%d}', '--footer=CONFIDENTIAL', '--right-footer=%p./%p#', '--chars-per-line=100', '--file-align=sheet', '--encoding=ISO-8859-1', '--output=%s' % _sFilePostscript] + sorted(lFiles))
        else:
            self._WARNING('Empty files list (Postscript file not created)')

    def a2ps(self, _sFilePostscript, _sFlag=None, _bBatch=False, _bForce=False):
        """
        Create a Postscript document with all (text) files in the configuration repository.
        (including validation, informational messages and exceptions handling)

        @param  string  _sFilePostscript  Postcript file (path)
        @param  string  _sFlag            File flag to match
        @param  bool    _bBatch           Batch mode (no confirmation prompts)
        @param  bool    _bForce           Forced batch mode
        """

        if _bForce: _bBatch = True

        try:

            # Confirmation
            if not _bBatch:
                if os.path.exists(_sFilePostscript):
                    if self._confirm('Overwrite existing file', ['y','n'])!='y':
                        return
                    self._rm(_sFilePostscript)
                else:
                    if os.path.exists(_sFilePostscript):
                        if not _bForce:
                            raise EnvironmentError(errno.EEXIST, 'File already exists')

            # Execute A2PS command
            return self._a2ps(_sFilePostscript, _sFlag, _bBatch, _bForce)

        except EnvironmentError as e:
            self._ERROR('%s; %s' % (e.strerror, _sFilePostscript))
            raise EnvironmentError(e.errno, 'Failed to create Postcript file')
