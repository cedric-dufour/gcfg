GIT-based Configuration Tracking Utility (GCFG)
===============================================

The objective of this utility is to allow the tracking and versioning of
(standard configuation) files on a system, in a manner that makes it easy to
have a global overview of how the system is configured and what changes were
performed.

By default, it uses a centralized repository in '/etc/gcfg' (though an alternate
directory may be specified when configuring the utility). This directory holds:
 - a GIT repository, used for versioning files changes
 - an "original backup" directory, used to keep a copy of original files
 - a "flag" directory, used to associate flags to files

Before issuing any 'gcfg' commands, one must first configure the utility envi-
ronment using the 'source gcfg.config' command. The purpose of this command is
both to verify/create the centralized repository and save the details of the
current author.

When a file is added ('gcfg new') or edited ('gcfg edit'):

 1. It is first moved within the scope of the GIT repository, keeping its
    absolute (but therefrom relative) path.
    Corresponding GIT commands ('gcfg log', 'gcfg diff', 'gcfg commit', etc.)
    then allows to keep track of all changes made to that file.

 2. The GIT-tracked file is then be symlinked back to its original/standard
    location.

 3. When specified, a copy of the original (pristine) version will be kept in
    the dedicated backup directory.
    The original version is then always handy thanks to the 'gcfg orig' command,
    while relative changes (diff) may be seen using the 'gcfg delta' command.

 4. Flags may also be associated to the file, for any purpose that may be
    required by the operator. One such flag is the "edit" flag, which is set as
    soon as the file is edited with 'gcfg edit'.
    Flags management is performed using the 'gcfg flag', 'gcfg flagged' and
    'gcfg unflag' commands.

A global overview of changes can then easily be obtained using the 'gcfg list'
command, or even saved in a Postscript file using the 'gcfg a2ps' command.
All modified files being within the scope of a single GIT repository, backup,
versions tracking and collaborative modifications may easily performed thanks
to GIT.


--

USAGE: gcfg <action> [<parameter> ...]

SYNOPSIS:
  Perform the requested action in the configuration repository.

ACTIONS:
  list
    List the content of the configuration repository

  a2ps <output-file>
    Create a Postscript document with all files in the configuration repository

  edit <file>
    Edit the given file (after adding it to the configuration repository)

  new [--batch] <file> [<original-file>]
    Add the given file to the configuration repository

  perm <file> [<mode> [<ownership>]]
    Show/change the permissions of the given file

  rm [--batch] <file>
    Remove the given file from the configuration repository

  add|log|diff <file> [<options> ...]
    Perform the corresponding GIT action on the given file 
    (see 'git help ...' for available options)

  status|commit|push [<options> ...]
    Perform the corresponding GIT action
    (see 'git help ...' for available options)

  orig <file>
    Show the original version of the given file

  delta <file> [<comment-prefix>='#']
    Show the differences between the given file and its original version,
    with all comments stripped out

  flag|flagged|unflag <file> [<flag>]
    Set|show/check|remove the specified flag for the given file

  verify
    Verify the consistency between the configuration repository and the actual
    files

