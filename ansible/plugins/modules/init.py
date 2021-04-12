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
module: init
version_added: unreleased
short_description: Initialize GCfg-tracking repository
description:
  - Create GCfg-tracking directory.
  - Initiliaze its GIT repository.
  - Create state-tracking sub-directories (original files, flags, etc.).
options:
  root:
    description:
      - GCfg root directory.
    type: path
    default: /etc/gcfg
seealso:
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
  gcfg.gcfg.init:
'''

RETURN = r'''
root:
    description: Path to GCfg root directory
    type: str
    sample: /etc/gcfg
git:
    description: Path to GCfg GIT repository
    type: str
    sample: /etc/gcfg/git
original:
    description: Path to GCfg original files sub-directory
    type: str
    sample: /etc/gcfg/original
flag:
    description: Path to GCfg flags sub-directory
    type: str
    sample: /etc/gcfg/flag
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
        ),
        supports_check_mode=True
    )

    # (arguments)
    root = module.params["root"]

    # Friendly exeception catching
    sys.excepthook = _ansible_excepthook

    # GCfg
    changed = False
    diff = {"before": {"root": root}, "after": {"root": root}}
    result = {"root": root}

    # (initialization)
    gcfg_exists = False
    try:
        gcfg = GCfgLib(
            "Ansible (gcfg.gcfg)",
            "{0}@{1}".format(pwd.getpwuid(os.getuid())[0], socket.gethostbyaddr(socket.gethostname())[0]),
            root,
        )
        gcfg.setSilent(True)
        try:
            gcfg_exists = gcfg.check(False, True)
        except Exception:
            pass
        if not gcfg_exists:
            changed = True
            diff["before"]["gcfg"] = "uninitialized"
            diff["after"]["gcfg"] = "initialized"
            if not module.check_mode:
                gcfg.check(True, True)
                gcfg_exists = True
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to initialize repository; {str(e)}")

    # Done
    result.update({"changed": changed, "diff": diff})
    if gcfg_exists:
        result.update({
            "git": gcfg.getRepositoryPath("git"),
            "original": gcfg.getRepositoryPath("original"),
            "flag": gcfg.getRepositoryPath("flag"),
        })
    module.exit_json(**result)


if __name__ == "__main__":
    main()
