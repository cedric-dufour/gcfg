#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2017, Ansible Project
# Copyright: (c) 2021, Cédric Dufour <http://cedric.dufour.name>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

# This is a virtual module that is entirely implemented as an action plugin and runs on the controller

from __future__ import absolute_import, division, print_function
__metaclass__ = type


DOCUMENTATION = r'''
---
module: template
version_added: unreleased
short_description: Template a file out to remote location and GCfg-track it
description:
  - The C(template) module templates a file from the local machine to a location on the remote machine.
  - See the M(ansible.gcfg.copy) for all options.
extends_documentation_fragment:
  - backup
  - files
  - template_common
  - validate
seealso:
  - module: ansible.gcfg.init
  - module: ansible.gcfg.file
  - module: ansible.gcfg.copy
  - module: ansible.builtin.template
author:
  - Ansible Core Team
  - Michael DeHaan
  - Cédric Dufour
'''

EXAMPLES = r'''
- name: Template file with owner and permissions
  gcfg.gcfg.template:
    src: "/mine/foo.txt.j2"
    dest: "/etc/foo.txt"
    owner: "foo"
    group: "foo"
    mode: "0644"

- name: Template a new "sudoers" file into place, after passing validation with visudo
  gcfg.gcfg.template:
    src: "/mine/sudoers.j2"
    dest: "/etc/sudoers"
    validate: "/usr/sbin/visudo -cf %s"
'''
