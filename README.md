GIT-based Configuration Tracking Utility (GCFG)
===============================================

The objective of the GIT-based Configuration Tracking Utility (GCFG) is to
allow the tracking and versioning of (mostly configuration) files on a system,
in a manner that makes it easy to have a global overview of how the system is
configured and what changes were made.

By default, it uses a centralized repository in `/etc/gcfg` (though an alternate
directory may be specified when configuring the utility). This directory holds:

 * a GIT (sub-)repository (`/etc/gcfg/git`), used for versioning changes

 * an "original" (sub-)repository (`/etc/gcfg/original`), used to keep a
   copy of original files

 * a "flag" (sub-)repository (`/etc/gcfg/flag`), used to associate flags
   to files

 * a packages listing file (`/etc/gcfg/pkglist`), which lists all the packages
   that are marked as "manually" installed

Before issuing any `gcfg` commands, one may first configure the utility environ-
ment (`GCFG_*` variables) using the `source gcfg` command.

When a file is added (`gcfg add`), copied (`gcfg copy`) or edited (`gcfg edit`):

 1. It is first moved within the scope of the GIT (sub-)repository.
    GIT commands (`gcfg git ...`) then allows to keep track of all changes
    made to that file.

 2. The GIT-tracked file is then linked back to its original/standard location,
    using either:
      - hard linking, by default
      - symbolic linking, in special directories like `/etc/cron.d`
      - file copy, when filesystems boundaries are crossed

 3. When specified, a copy of the original version is kept in the "original"
    (sub-)repository.
    The original version is then always handy thanks to the `gcfg orig`
    command, while changes relative to that original version may be seen
    using the `gcfg delta` command.

 4. Flags can also be associated to the file, for any purpose that may be
    required by the operator.
    One such flag is the `@EDITED` flag, which is set as soon as the file
    has been modified with `gcfg edit`.
    Flags management is performed using the `gcfg flag`, `gcfg unflag` and
    `gcfg flagged` commands.

A global overview of changes can then easily be obtained using the `gcfg list`
command, or even saved in a Postscript file using the `gcfg a2ps` command.

All modified files being within the scope of a single GIT repository, backup,
versions tracking and collaborative management are easily performed thanks
to GIT.

--

``` text
usage: gcfg <command>

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
```
