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
import tempfile

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils._text import to_bytes, to_native

from gcfg import GCfgLib


module = None

DOCUMENTATION = r"""
---
module: pkgsave
version_added: unreleased
short_description: Update the GCfg-tracked list of manually-installed packages
description:
  - Update manually-installed packages (apt-mark showmanual / gcfg pkgsave).
options:
  root:
    description:
      - GCfg root directory.
    type: path
    default: /etc/gcfg
seealso:
  - module: gcfg.gcfg.init
  - module: gcfg.gcfg.commit
author:
  - Ansible Core Team
  - Michael DeHaan
  - Cédric Dufour
"""

EXAMPLES = r"""
- name: Update the GCfg-tracked list of manually-installed packages
  gcfg.gcfg.pkgsave:
"""

RETURN = r"""
root:
    description: Path to GCfg root directory
    type: str
    sample: /etc/gcfg
packages:
    description: List of manually installed packages
    type: list
    sample: sample
"""


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

    changed = False
    diff = {"before": {"root": root}, "after": {"root": root}}
    result = {"root": root}

    # (pkglist)
    try:
        packages_before = gcfg.pkglist().splitlines()
        packages_before.sort()
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to retrieve packages list; {str(e)}")

    # (pkgsave)
    if not module.check_mode:
        pkglist = gcfg.getRepositoryPath("pkglist")
        b_pkglist = to_bytes(pkglist, errors="surrogate_or_strict")
    else:
        (_, b_pkglist) = tempfile.mkstemp()
        pkglist = to_native(b_pkglist)
    try:
        gcfg.pkglist(pkglist)
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to update packages list; {str(e)}")
    try:
        with open(b_pkglist, "r") as f:
            packages_after = f.read().splitlines()
            packages_after.sort()
    except Exception as e:
        module.fail_json(msg=f"[GCfg] Failed to retrieve updated packages list; {str(e)}")
    if packages_after != packages_before:
        changed = True
        diff["before"]["packages"] = packages_before
        diff["after"]["packages"] = packages_after

    # Done
    result.update({"changed": changed, "diff": diff, "packages": packages_after})
    module.exit_json(**result)


if __name__ == "__main__":
    main()
