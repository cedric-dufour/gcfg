#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2012, Michael DeHaan <michael.dehaan@gmail.com>
# Copyright: (c) 2017, Ansible Project
# Copyright: (c) 2021, Cédric Dufour <http://cedric.dufour.name>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import os
import pwd
import socket
import sys

from ansible.module_utils.basic import AnsibleModule

from gcfg import GCfgLib


module = None

DOCUMENTATION = r'''
---
module: commit
version_added: unreleased
short_description: GIT-commit a GCfg checkpoint
description:
  - Add all modified files (git add).
  - Commit the changes with the user-specified message (git commit).
  - Tag the commit with the user-specified tag (git tag).
options:
  root:
    description:
      - GCfg root directory.
    type: path
    default: /etc/gcfg
  tag:
    description:
      - GIT tag.
    type: str
    required: yes
  message:
    description:
      - GIT commit message.
    type: str
    required: yes
  author:
    description:
      - GIT commit author.
    type: str
    default: Ansible (gcfg.gcfg)
  email:
    description:
      - GIT commit author.
    type: str
    default: username@hostname (as seen by "getpwuid" and "gethostbyaddr")
seealso:
  - module: gcfg.gcfg.init
  - module: gcfg.gcfg.file
  - module: gcfg.gcfg.copy
  - module: gcfg.gcfg.template
author:
  - Ansible Core Team
  - Michael DeHaan
  - Cédric Dufour
'''

EXAMPLES = r'''
- name: Initialize GCfg-tracking repository
  gcfg.gcfg.commit:
    tag: "sample"
    message: "Sample commit message"
'''

RETURN = r'''
root:
    description: Path to GCfg root directory
    type: str
    sample: /etc/gcfg
tag:
    description: Path to GCfg GIT repository
    type: str
    sample: sample
commit:
    description: Commit ID (checksum)
    type: str
    sample: 84b30f780ae1d5682421e493cbc9ca67718b0936
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


def main():

    # Ansible module
    global module
    module = AnsibleModule(
        argument_spec=dict(
            root=dict(type="path", default="/etc/gcfg"),
            tag=dict(type="str", required=True),
            message=dict(type="str", required=True),
            author=dict(type="str", default="Ansible (gcfg.gcfg)"),
            email=dict(type="str", default="{0}@{1}".format(pwd.getpwuid(os.getuid())[0], socket.gethostbyaddr(socket.gethostname())[0])),
        ),
        supports_check_mode=True
    )

    # (arguments)
    root = module.params["root"]
    tag = module.params["tag"]
    message = module.params["message"]
    author = module.params["author"]
    email = module.params["email"]

    # Friendly exeception catching
    sys.excepthook = _ansible_excepthook

    # GCfg
    try:
        gcfg = GCfgLib(author, email, root)
        gcfg.setSilent(True)
        gcfg.check(False, True)
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to check repository; {str(e)}")

    changed = False
    diff = {"before": {"root": root}, "after": {"root": root}}
    result = {"root": root}

    # (tag)
    tag_exists = False
    try:
        if gcfg.git(["tag", "-l", tag], True).strip() == tag:
            tag_exists = True
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to list GIT tag; {str(e)}")

    # (commit)
    commit = "unknown"
    if not tag_exists:
        changed = True
        diff["before"]["tag"] = "missing"
        diff["after"]["tag"] = commit
        if not module.check_mode:
            try:
                gcfg.git(["add", "--all"], True)
                gcfg.git(["commit", "--message", message], True)
                gcfg.git(["tag", tag, "HEAD"], True)
                commit = gcfg.git(["rev-list", "-n", "1", tag], True).strip()
                diff["after"]["tag"] = commit
            except Exception as e:
                module.fail_json(msg=f"[GCfg] Failed to commit GIT checkpoint; {str(e)}")
    else:
        try:
            commit = gcfg.git(["rev-list", "-n", "1", tag], True).strip()
        except Exception as e:
            module.fail_json(msg=f"[GCfg] Failed to retrieve GIT commit; {str(e)}")

    # Done
    result.update({"changed": changed, "diff": diff, "tag": tag, "commit": commit})
    module.exit_json(**result)


if __name__ == "__main__":
    main()
