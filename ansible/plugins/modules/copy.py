#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2017, Ansible Project
# Copyright: (c) 2021, Cédric Dufour <http://cedric.dufour.name>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import errno
import os
import os.path
import pwd
import shutil
import socket
import stat
import sys
import tempfile
import traceback

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes, to_native

from gcfg import GCfgLib


module = None

DOCUMENTATION = r'''
---
module: copy
version_added: unreleased
short_description: Copy a file to remote location and GCfg-track it
description:
  - The C(copy) module copies a file from the local or remote machine to a location on the remote
    machine.
  - If you need variable interpolation in copied files, use the M(ansible.gcfg.template) module
    Using a variable in the C(content) field will result in unpredictable output.
  - See the M(ansible.gcfg.file) for common options (file attributes, flags, etc.).
options:
  root:
    description:
      - GCfg root directory.
    type: path
    default: /etc/gcfg
  src:
    description:
    - Local path to a file to copy to the remote server.
    - This can be absolute or relative.
    type: path
  content:
    description:
      - When used instead of C(src), sets the contents of a file directly to the specified value.
      - For advanced formatting or if C(content) contains a variable, use the
        M(ansible.gcfg.template) module.
    type: str
  dest:
    description:
      - Remote absolute path where the file should be copied to.
    type: path
    required: yes
  backup:
    description:
      - Create a backup of the original file (gcfg original), which can be used to show the
        differences with the actual file (gcfg delta) or when removing the actual file from GCfg
        tracking and restore the original version.
        This works only when the file is initially added for GCfg tracking.
    type: bool
    default: yes
  original:
    description:
      - Alternate path to the original file (to backup).
    type: path
  flag:
    description:
      - Textual flags to add to the file (gcfg flag).
    type: list
  unflag:
    description:
      - Textual flags to remove from the file (gcfg unflag).
      - Use C(@ALL) to strip all existing flags (except those specified by I(flag))
    type: list
  force:
    description:
      - Influence whether the remote file must always be replaced.
      - If C(yes), the remote file will be replaced when contents are different than the source.
      - If C(no), the file will only be transferred if the destination does not exist.
    type: bool
    default: yes
  remote_src:
    description:
      - Influence whether C(src) needs to be transferred or already is present remotely.
      - If C(no), it will search for C(src) at originating/master machine.
      - If C(yes) it will go to the remote/target machine for the C(src).
      - C(remote_src) only works with C(mode=preserve) as of version 2.6.
    type: bool
    default: no
  checksum:
    description:
      - SHA1 checksum of the file being transferred.
      - Used to validate that the copy of the file was successful.
      - If this is not provided, ansible will use the local calculated checksum of the src file.
    type: str
extends_documentation_fragment:
  - backup
  - decrypt
  - files
  - validate
seealso:
  - module: gcfg.gcfg.init
  - module: gcfg.gcfg.file
  - module: gcfg.gcfg.template
  - module: ansible.builtin.copy
author:
  - Ansible Core Team
  - Michael DeHaan
  - Cédric Dufour
'''

EXAMPLES = r'''
- name: Copy file with owner and permissions
  gcfg.gcfg.copy:
    src: "/mine/foo.txt"
    dest: "/etc/foo.txt"
    owner: "foo"
    group: "foo"
    mode: "0644"

- name: Copy a new "sudoers" file into place, after passing validation with visudo
  gcfg.gcfg.copy:
    src: "/mine/sudoers"
    dest: "/etc/sudoers"
    validate: "/usr/sbin/visudo -csf %s"

- name: Copy using inline content
  gcfg.gcfg.copy:
    content: "# This file was moved to /etc/foo.txt"
    dest: "/etc/bar.txt"
'''

RETURN = r'''
state:
    description: State of the target, after execution
    returned: success
    type: str
    sample: hard
dest:
    description: Destination file/path
    returned: success
    type: str
    sample: /etc/foo.txt
src:
    description: Source file/path
    returned: success
    type: str
    sample: /mine/foo.txt
backup_file:
    description: Name of backup file created
    returned: changed and if backup=yes
    type: str
    sample: /etc/gcfg/original/etc/foo.txt
flags:
    description: Textual flags associated to file (as per I(flag)/I(unflag))
    returned: state=present, state=hard, state=link, state=file
    type: list
    sample: ["@ANSIBLE", "examples"]
checksum:
    description: SHA1 checksum of the file after running copy
    returned: success
    type: str
    sample: 6e642bb8dd5c2e027bf21dd923337cbb4214f827
'''


class AnsibleModuleError(Exception):
    def __init__(self, results):
        self.results = results

    def __repr__(self):
        print("AnsibleModuleError(results={0})".format(self.results))


class ParameterError(AnsibleModuleError):
    pass


class Sentinel(object):
    def __new__(cls, *args, **kwargs):
        return cls


def _ansible_excepthook(exc_type, exc_value, tb):
    # Using an exception allows us to catch it if the calling code knows it can recover
    if issubclass(exc_type, AnsibleModuleError):
        module.fail_json(**exc_value.results)
    else:
        sys.__excepthook__(exc_type, exc_value, tb)


def _state_ansible2gcfg(state):
    gcfg_state = None
    if state == "hard":
        gcfg_state = "hardlink"
    elif state == "link":
        gcfg_state = "symlink"
    elif state == "copy":
        gcfg_state = "copy"
    return gcfg_state


def _state_gcfg2ansible(gcfg_state):
    state = "present"
    if gcfg_state is None:
        state = "absent"
    elif gcfg_state == "hardlink":
        state = "hardlink"
    elif gcfg_state == "symlink":
        state = "link"
    elif gcfg_state == "copy":
        state = "copy"
    return state


def main():

    # Ansible module
    global module
    module = AnsibleModule(
        # not checking because of daisy chain to file module
        argument_spec=dict(
            root=dict(type="path", default="/etc/gcfg"),
            state=dict(type="str", choices=["present", "hard", "link", "copy"], default="present"),
            src=dict(type="path"),
            content=dict(type="str", no_log=True),
            dest=dict(type="path", required=True),
            backup=dict(type="bool", default=True),
            original=dict(type="path"),
            flag=dict(type="list"),
            unflag=dict(type="list"),
            force=dict(type="bool", default=True),
            checksum=dict(type="str"),
            validate=dict(type="str"),
            remote_src=dict(type="bool"),
        ),
        add_file_common_args=True,
        supports_check_mode=True,
    )

    # (arguments)
    root = module.params["root"]
    state = module.params["state"]
    src = module.params["src"]
    dest = module.params["dest"]
    backup = module.params["backup"]
    original = module.params["original"]
    flag = module.params["flag"] or []
    unflag = module.params["unflag"] or []
    force = module.params["force"]
    checksum = module.params["checksum"]
    validate = module.params["validate"]
    remote_src = module.params["remote_src"]
    # (alias)
    path = dest
    # (<-> attributes)
    file_params = module.load_file_common_arguments(module.params)
    owner = file_params["owner"]
    group = file_params["group"]
    mode = file_params["mode"]

    # (to_bytes)
    b_src = to_bytes(src, errors="surrogate_or_strict")
    b_path = to_bytes(path, errors="surrogate_or_strict")
    #b_original = to_bytes(original, errors="surrogate_or_strict")

    # Friendly exeception catching
    sys.excepthook = _ansible_excepthook

    # Validation

    # (arguments)
    if validate and "%s" not in validate:
        module.fail_json(msg=f"'validate' must contain %s: {validate}")

    # (source)
    if not os.path.exists(b_src):
        module.fail_json(msg=f"Source {src} not found")
    if src.endswith(os.sep) or os.path.isdir(b_src):
        module.fail_json(msg=f"Source {src} may not be a directory")
    if not os.access(b_src, os.R_OK):
        module.fail_json(msg=f"Source {src} not readable")

    # (destination)
    if path.endswith(os.sep) or os.path.isdir(b_path):
        module.fail_json(msg=f"Destination {path} may not be a directory")
    if os.path.exists(b_path):
        if not force:
            module.exit_json(msg="Destination already exists", src=src, dest=path, changed=False)
        if not os.access(b_path, os.W_OK):
            module.fail_json(msg=f"Destination {path} not writable")
    else:
        b_path_dir = os.path.dirname(b_path)
        path_dir = to_native(b_path_dir)
        if not os.path.exists(b_path_dir):
            try:
                os.stat(b_path_dir)
            except OSError as e:
                if "permission denied" in to_native(e).lower():
                    module.fail_json(msg=f"Destination directory {path_dir} is not accessible")
            module.fail_json(msg=f"Destination directory {path_dir} does not exist")
        if not os.access(b_path_dir, os.W_OK) and not module.params["unsafe_writes"]:
            module.fail_json(msg=f"Destination directory {path_dir} not writable")

    # (checksum)
    if checksum:
        checksum_src = module.sha1(src)
        if checksum_src != checksum:
            module.fail_json(
                msg="Copied file does not match the expected checksum. Transfer failed.",
                checksum=checksum_src,
                expected_checksum=checksum,
            )

    # Mode + remote_src has to be done on the remote host
    if remote_src and mode == 'preserve':
        mode = '0%03o' % stat.S_IMODE(os.stat(b_src).st_mode)

    # GCfg
    try:
        gcfg = GCfgLib(
            "Ansible (gcfg.gcfg)",
            "{0}@{1}".format(pwd.getpwuid(os.getuid())[0], socket.gethostbyaddr(socket.gethostname())[0]),
            root,
        )
        gcfg.setSilent(True)
        gcfg.check(False, True)
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to check repository; {str(e)}")

    # (resources)
    try:
        path_git = gcfg.getRepositoryPath("git", path)
        b_path_git = to_bytes(path_git, errors="surrogate_or_strict")
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to retrieve {path} GIT path; {str(e)}")
    path_orig = None
    #b_path_orig = None
    if backup:
        try:
            path_orig = gcfg.getRepositoryPath("original", path)
            #b_path_orig = to_bytes(path_orig, errors="surrogate_or_strict")
        except Exception as e:
            module.fail_json(msg=f"[GCfg] Failed to retrieve {path} original (backup) path; {str(e)}")

    # Validation (cont'd)
    if not os.path.exists(b_path_git):  # file is untracked
        if os.path.islink(b_path):
            module.fail_json(msg=f"Destination {path} may not be a symbolic link")
        if os.path.exists(b_path) and os.stat(b_path).st_nlink > 1:
            module.fail_json(msg=f"Destination {path} may not be a hard link")

    # State
    try:
        (gcfg_unchanged, gcfg_current_state) = gcfg.isLinked(path)
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to retrieve {path} status; {str(e)}")
    gcfg_target_state = _state_ansible2gcfg(state)

    # Validation (cont'd)
    if not gcfg_unchanged and validate:
        # make sure temporary file source has proper permissions
        if mode is not None:
            module.set_mode_if_different(src, mode, False)
        if owner is not None:
            module.set_owner_if_different(src, owner, False)
        if group is not None:
            module.set_group_if_different(src, group, False)
        (rc, out, err) = module.run_command(validate % src)
        if rc != 0:
            module.fail_json(msg="Failed to validate source", exit_status=rc, stdout=out, stderr=err)

    # Flags
    if gcfg_current_state is not None:
        try:
            gcfg_current_flags = gcfg.flagged(path, None)
        except Exception as e:
            module.fail_json(msg=f"[GCfg] Failed to retrieve {path} flags; {str(e)}")
    else:
        gcfg_current_flags = []
    if "@ALL" in unflag:
        gcfg_target_flags = []
    else:
        gcfg_target_flags = gcfg_current_flags.copy()
        for f in unflag:
            if f in gcfg_target_flags:
                gcfg_target_flags.remove(f)
    for f in flag:
        if f not in gcfg_target_flags:
            gcfg_target_flags.append(f)
    if "@ANSIBLE" not in gcfg_target_flags:
        gcfg_target_flags.append("@ANSIBLE")
    gcfg_current_flags.sort()
    gcfg_target_flags.sort()

    # GCfg (cont'd)
    changed = False
    diff = {"before": {"dest": dest}, "after": {"dest": dest}}
    result = {"src": src, "dest": dest}

    # (validate + add/copy)
    if not os.path.exists(b_path_git):  # file is untracked
        changed = True
        diff["before"]["gcfg"] = "untracked"
        diff["after"]["gcfg"] = "tracked"

        if not module.check_mode:

            # Track existing file (add, including backup)
            path_exists = os.path.exists(b_path)
            if path_exists:
                gcfg_original = False
                if backup:
                    if original is not None:
                        gcfg_original = original
                    else:
                        gcfg_original = True
                    result.update({"backup_file": path_orig})
                try:
                    gcfg.add(path, gcfg_original, gcfg_target_state, True, True)
                except Exception as e:
                    module.fail_json(msg=f"[GCfg] Failed to add {path}; {str(e)}")

            # Copy (src -> dest)
            try:
                b_mysrc = b_src
                if remote_src:
                    (_, b_mysrc) = tempfile.mkstemp(dir=os.path.dirname(b_path))
                    shutil.copyfile(b_src, b_mysrc)
                    try:
                        shutil.copystat(b_src, b_mysrc)
                    except OSError as err:
                        if err.errno == errno.ENOSYS and mode == "preserve":
                            module.warn(f"Failed to copy {src} stats")
                        else:
                            raise

                module.atomic_move(b_mysrc, path, unsafe_writes=module.params["unsafe_writes"])

                if not remote_src:
                    try:
                        acl_command = ["setfacl", "-b", path]
                        b_acl_command = [to_bytes(x) for x in acl_command]
                        (rc, out, err) = module.run_command(b_acl_command, environ_update=dict(LANG="C", LC_ALL="C", LC_MESSAGES="C"))
                        if rc != 0:
                            raise RuntimeError(f"Failed to clear {path} ACLs; {err}")
                    except Exception as e:
                        if "Operation not supported" in to_native(e):
                            # The file system does not support ACLs.
                            pass
                        else:
                            raise

            except OSError:
                module.fail_json(msg="Failed to copy {src} to {path}", traceback=traceback.format_exc())

            # Re-link
            if os.path.exists(b_path_git):  # file is already tracked
                try:
                    gcfg.link(path, gcfg_target_state, True, True)
                except Exception as e:
                    module.fail_json(msg=f"[GCfg] Failed to (re)link {path}; {str(e)}")

            # Track non (previously) existing file (add, including backup of alternative original)
            elif not path_exists:
                gcfg_original = False
                if backup and original is not None:
                    gcfg_original = original
                    result.update({"backup_file": path_orig})
                try:
                    gcfg.add(path, gcfg_original, gcfg_target_state, True, True)
                except Exception as e:
                    module.fail_json(msg=f"[GCfg] Failed to add {path}; {str(e)}")

    # (link)
    elif not gcfg_unchanged or (state != "present" and gcfg_current_state != gcfg_target_state):
        changed = True
        diff["before"]["state"] = gcfg_current_state
        diff["after"]["state"] = gcfg_target_state
        if not module.check_mode:
            try:
                gcfg.link(path, gcfg_target_state, True, True)
            except Exception as e:
                module.fail_json(msg=f"[GCfg] Failed to (re)link {path} ({state}); {str(e)}")

    # (flags)
    if gcfg_target_flags != gcfg_current_flags:
        changed = True
        diff["before"]["flags"] = gcfg_current_flags
        diff["after"]["flags"] = gcfg_target_flags
        if not module.check_mode:
            try:
                for f in gcfg_target_flags:
                    if f not in gcfg_current_flags:
                        gcfg.flag(path, f, True)
                for f in gcfg_current_flags:
                    if f not in gcfg_target_flags:
                        gcfg.unflag(path, f)
            except Exception as e:
                module.fail_json(msg=f"[GCfg] Failed to (un)flag {path} ({state}); {str(e)}")

    # Attributes
    if changed and not module.check_mode:
        # (GCfg might have altered the state)
        (_, gcfg_target_state) = gcfg.isLinked(path)
    if gcfg_target_state == "copy" or gcfg_target_state == "hardlink":
        changed = module.set_fs_attributes_if_different(file_params, changed, diff, expand=False)
    if gcfg_current_state is not None:
        file_params["path"] = path_git
        changed = module.set_fs_attributes_if_different(file_params, changed, diff, expand=False)

    # Done
    state = _state_gcfg2ansible(gcfg_target_state)
    result.update({"state": state, "flags": gcfg_target_flags, "checksum": checksum, "changed": changed, "diff": diff})
    module.exit_json(**result)


if __name__ == "__main__":
    main()
