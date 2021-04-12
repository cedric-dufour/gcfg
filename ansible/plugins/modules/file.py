#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2017, Ansible Project
# Copyright: (c) 2021, Cédric Dufour <http://cedric.dufour.name>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import os.path
import pwd
import socket
import sys

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes

from gcfg import GCfgLib


module = None

DOCUMENTATION = r'''
---
module: file
version_added: unreleased
short_description: Manage a remote GCfg-tracked file and its properties
description:
  - Add (link) file for GCfg tracking (gcfg add).
  - Set attributes of GCfg-tracked file.
  - Set flags on GCfg-tracked file (gcfg flag/unflag).
  - Alternatively, remove GCfg-tracked file (restore original).
  - Many other modules support the same options as the C(file) module - including M(ansible.gcfg.copy),
    and M(ansible.gcfg.template).
options:
  root:
    description:
      - GCfg root directory.
    type: path
    default: /etc/gcfg
  state:
    description:
      - If C(present), file is added (linked) to GCfg using best linking method.
      - If C(hard), file is linked using a hard link (preferred).
      - If C(link), file is linked using a symbolic link (e.g. cron files).
      - If C(copy), file is "linked" using a copy (e.g. across filesystems).
      - If C(absent), remove the file from GCfg. If the original file is available, it is restored
        in place of the current file. Otherwise the file is deleted.
    type: str
    default: present
    choices: [ present, hard, link, copy, absent ]
  path:
    description:
      - Path to the file being managed.
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
extends_documentation_fragment:
  - backup
  - files
seealso:
  - module: gcfg.gcfg.init
  - module: gcfg.gcfg.copy
  - module: gcfg.gcfg.template
  - module: ansible.builtin.file
author:
  - Ansible Core Team
  - Michael DeHaan
  - Cédric Dufour
'''

EXAMPLES = r'''
- name: Change file ownership, group and permissions
  gcfg.gfcg.file:
    path: "/etc/foo.txt"
    flag: ["examples"]
    owner: "foo"
    group: "foo"
    mode: "0644"

- name: Remove file (delete file / restore its original version)
  gcfg.gfcg.file:
    path: "/etc/foo.txt"
    state: absent
'''

RETURN = r'''
state:
    description: State of the target, after execution
    returned: success
    type: str
    sample: hard
path:
    description: File/path, equal to the value passed to I(path)
    returned: state=present, state=hard, state=link, state=file
    type: str
    sample: /path/to/file.txt
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
group:
    description: Group of the file, after execution
    returned: success
    type: str
    sample: foo
gid:
    description: Group id of the file, after execution
    returned: success
    type: int
    sample: 1000
owner:
    description: Owner of the file, after execution
    returned: success
    type: str
    sample: foo
uid:
    description: Owner id of the file, after execution
    returned: success
    type: int
    sample: 1000
mode:
    description: Permissions of the target, after execution
    returned: success
    type: str
    sample: 0644
size:
    description: Size of the target, after execution
    returned: success
    type: int
    sample: 1220
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


def test_appears_binary(path):
    """Take a guess as to whether a file is a binary file"""
    b_path = to_bytes(path, errors="surrogate_or_strict")
    appears_binary = False
    try:
        with open(b_path, "rb") as f:
            head = f.read(8192)
    except Exception:
        # If we can't read the file, we're okay assuming it's text
        pass
    else:
        if b"\x00" in head:
            appears_binary = True

    return appears_binary


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
        argument_spec=dict(
            root=dict(type="path", default="/etc/gcfg"),
            state=dict(type="str", choices=["present", "hard", "link", "copy", "absent"], default="present"),
            path=dict(type="path", required=True),
            backup=dict(type="bool", default=True),
            original=dict(type="path"),
            flag=dict(type="list"),
            unflag=dict(type="list"),
            _diff_peek=dict(type="bool"),  # Internal use only, for internal checks in the action plugins
        ),
        add_file_common_args=True,
        supports_check_mode=True,
    )

    # (arguments)
    root = module.params["root"]
    state = module.params["state"]
    path = module.params["path"]
    backup = module.params["backup"]
    original = module.params["original"]
    flag = module.params["flag"] or []
    unflag = module.params["unflag"] or []
    # (<-> attributes)
    file_params = module.load_file_common_arguments(module.params)

    # (to_bytes)
    b_path = to_bytes(path, errors="surrogate_or_strict")
    #b_original = to_bytes(original, errors="surrogate_or_strict")

    # Friendly exeception catching
    sys.excepthook = _ansible_excepthook

    # Short-circuit for diff_peek
    if module.params["_diff_peek"] is not None:
        appears_binary = test_appears_binary(path)
        module.exit_json(path=path, changed=False, appears_binary=appears_binary)

    # Validation
    if path.endswith(os.sep) or os.path.isdir(b_path):
        module.fail_json(msg=f"Location {path} may not be a directory")
    if not os.path.exists(b_path):
        module.fail_json(msg=f"Location {path} must exist")
    if not os.access(b_path, os.W_OK):
        module.fail_json(msg=f"Location {path} not writable")

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
            module.fail_json(msg=f"Location {path} may not be a symbolic link")
        if os.stat(b_path).st_nlink > 1:
            module.fail_json(msg=f"Location {path} may not be a hard link")

    # State
    try:
        (gcfg_unchanged, gcfg_current_state) = gcfg.isLinked(path)
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to retrieve {path} status; {str(e)}")
    gcfg_target_state = _state_ansible2gcfg(state)

    # GCfg (cont'd)
    changed = False
    diff = {"before": {"path": path}, "after": {"path": path}}
    result = {"path": path}

    # (remove)
    if state == "absent":
        if os.path.exists(b_path_git):
            changed = True
            diff["before"]["gcfg"] = "tracked"
            diff["after"]["gcfg"] = "untracked"
            if not module.check_mode:
                try:
                    gcfg.remove(path, True, True)
                except Exception as e:
                    module.fail_json(msg=f"[GCfg] Failed to remove {path}; {str(e)}")

        # Done
        result.update({"changed": changed, "diff": diff, "state": state})
        module.exit_json(**result)

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

    # (add)
    if not os.path.exists(b_path_git):  # file is untracked
        changed = True
        diff["before"]["gcfg"] = "untracked"
        diff["after"]["gcfg"] = "tracked"
        if not module.check_mode:
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
    result.update({"state": state, "flags": gcfg_target_flags, "changed": changed, "diff": diff})
    module.exit_json(**result)


if __name__ == "__main__":
    main()
