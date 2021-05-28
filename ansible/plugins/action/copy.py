# (c) 2012-2014, Michael DeHaan <michael.dehaan@gmail.com>
# (c) 2017 Toshio Kuratomi <tkuraotmi@ansible.com>
# (c) 2021, Cédric Dufour <http://cedric.dufour.name>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

import json
import os
import os.path
import stat
import tempfile
import traceback

from ansible import constants as C
from ansible.errors import AnsibleError, AnsibleFileNotFound
from ansible.module_utils.basic import FILE_COMMON_ARGUMENTS
from ansible.module_utils._text import to_bytes, to_native, to_text
from ansible.module_utils.parsing.convert_bool import boolean
from ansible.plugins.action import ActionBase
from ansible.utils.hashing import checksum


REAL_FILE_ARGS = frozenset(FILE_COMMON_ARGUMENTS.keys()).union(
    ('root', 'state', 'path', 'backup', 'original', 'flag', 'unflag')
)


def _create_remote_file_args(module_args):
    return dict((k, v) for k, v in module_args.items() if k in REAL_FILE_ARGS)


def _create_remote_copy_args(module_args):
    """remove action plugin only keys"""
    return dict((k, v) for k, v in module_args.items() if k not in ("content", "decrypt"))


class ActionModule(ActionBase):

    TRANSFERS_FILES = True

    def _ensure_invocation(self, result):
        # NOTE: adding invocation arguments here needs to be kept in sync with
        # any no_log specified in the argument_spec in the module.
        # This is not automatic.
        # NOTE: do not add to this. This should be made a generic function for action plugins.
        # This should also use the same argspec as the module instead of keeping it in sync.
        if "invocation" not in result:
            if self._play_context.no_log:
                result["invocation"] = "CENSORED: no_log is set"
            else:
                # NOTE: Should be removed in the future. For now keep this broken
                # behaviour, have a look in the PR 51582
                result["invocation"] = self._task.args.copy()
                result["invocation"]["module_args"] = self._task.args.copy()

        if isinstance(result["invocation"], dict):
            if "content" in result["invocation"]:
                result["invocation"]["content"] = "CENSORED: content is a no_log parameter"
            if result["invocation"].get("module_args", {}).get("content") is not None:
                result["invocation"]["module_args"]["content"] = "VALUE_SPECIFIED_IN_NO_LOG_PARAMETER"

        return result

    def _copy_file(self, source_full, source_rel, content, content_tempfile, dest, task_vars):
        decrypt = boolean(self._task.args.get("decrypt", True), strict=False)
        force = boolean(self._task.args.get("force", "yes"), strict=False)
        raw = boolean(self._task.args.get("raw", "no"), strict=False)

        result = {"diff": []}
        content_changed = False

        # If the local file does not exist, get_real_file() raises AnsibleFileNotFound
        try:
            source_full = self._loader.get_real_file(source_full, decrypt=decrypt)
        except AnsibleFileNotFound as e:
            result["failed"] = True
            result["msg"] = "could not find src=%s, %s" % (source_full, to_text(e))
            return result

        # Get the local mode and set if user wanted it preserved
        # https://github.com/ansible/ansible-modules-core/issues/1124
        lmode = None
        if self._task.args.get("mode", None) == "preserve":
            lmode = "0%03o" % stat.S_IMODE(os.stat(source_full).st_mode)

        # Attempt to get remote file info
        dest_status = self._execute_remote_stat(dest, all_vars=task_vars, follow=True, checksum=force)

        if dest_status["exists"] and dest_status["isdir"]:
            # The dest is a directory.
            result["failed"] = True
            result["msg"] = "can not use a dir as dest"
            return result

        if dest_status["exists"] and not force:
            return None

        # Generate a hash of the local file.
        local_checksum = checksum(source_full)

        # Show differences
        if local_checksum != dest_status["checksum"]:
            content_changed = True
            if self._play_context.diff and not raw:
                result["diff"].append(self._get_diff_data(dest, source_full, task_vars))
            if self._play_context.check_mode:
                self._remove_tempfile_if_content_defined(content, content_tempfile)
                result["changed"] = True
                return result

        # Define a remote directory that we will copy the file to.
        tmp_src = self._connection._shell.join_path(self._connection._shell.tmpdir, "source")

        # Transfer the file
        remote_path = None
        if not raw:
            remote_path = self._transfer_file(source_full, tmp_src)
        else:
            self._transfer_file(source_full, dest)

        # FIXME: I don't think this is needed when PIPELINING=0 because the source is created
        # world readable.  Access to the directory itself is controlled via fixup_perms2() as
        # part of executing the module. Check that umask with scp/sftp/piped doesn't cause
        # a problem before acting on this idea. (This idea would save a round-trip)
        # fix file permissions when the copy is done as a different user
        if remote_path:
            self._fixup_perms2((self._connection._shell.tmpdir, remote_path))

        # We no longer require our content_tempfile
        self._remove_tempfile_if_content_defined(content, content_tempfile)
        self._loader.cleanup_tmp_file(source_full)

        if raw:
            return None

        # Run the copy module

        new_module_args = _create_remote_copy_args(self._task.args)
        new_module_args.update({"src": tmp_src, "_content_changed": content_changed})
        if not self._task.args.get("checksum"):
            new_module_args["checksum"] = local_checksum

        if lmode:
            new_module_args["mode"] = lmode

        module_return = self._execute_module(module_name="gcfg.gcfg.copy", module_args=new_module_args, task_vars=task_vars)

        if not module_return.get("checksum"):
            module_return["checksum"] = local_checksum

        result.update(module_return)
        return result

    def _create_content_tempfile(self, content):
        ''' Create a tempfile containing defined content '''
        fd, content_tempfile = tempfile.mkstemp(dir=C.DEFAULT_LOCAL_TMP)
        f = os.fdopen(fd, "wb")
        content = to_bytes(content)
        try:
            f.write(content)
        except Exception as err:
            os.remove(content_tempfile)
            raise Exception(err)
        finally:
            f.close()
        return content_tempfile

    def _remove_tempfile_if_content_defined(self, content, content_tempfile):
        if content is not None:
            os.remove(content_tempfile)

    def run(self, tmp=None, task_vars=None):
        ''' handler for file transfer operations '''
        if task_vars is None:
            task_vars = dict()

        result = super(ActionModule, self).run(tmp, task_vars)
        del tmp  # tmp no longer has any effect

        state = self._task.args.get("state", None)
        src = self._task.args.get("src", None)
        content = self._task.args.get("content", None)
        dest = self._task.args.get("dest", None)
        remote_src = boolean(self._task.args.get("remote_src", False), strict=False)

        if state == 'absent':
            new_module_args = _create_remote_file_args(self._task.args)
            new_module_args['path'] = dest
            result.update(self._execute_module(module_name="gcfg.gcfg.file", module_args=new_module_args, task_vars=task_vars))
            return self._ensure_invocation(result)

        result["failed"] = True
        if not src and content is None:
            result["msg"] = "src (or content) is required"
        elif not dest:
            result["msg"] = "dest is required"
        elif src and content is not None:
            result["msg"] = "src and content are mutually exclusive"
        else:
            del result["failed"]

        if result.get("failed"):
            return self._ensure_invocation(result)

        # Define content_tempfile in case we set it after finding content populated.
        content_tempfile = None

        # If content is defined make a tmp file and write the content into it.
        if content is not None:
            try:
                # If content comes to us as a dict it should be decoded json.
                # We need to encode it back into a string to write it out.
                if isinstance(content, dict) or isinstance(content, list):
                    content_tempfile = self._create_content_tempfile(json.dumps(content))
                else:
                    content_tempfile = self._create_content_tempfile(content)
                src = content_tempfile
            except Exception as err:
                result["failed"] = True
                result["msg"] = "could not write content temp file: %s" % to_native(err)
                return self._ensure_invocation(result)

        # if we have first_available_file in our vars
        # look up the files and use the first one we find as src
        elif remote_src:
            result.update(self._execute_module(module_name="gcfg.gcfg.copy", task_vars=task_vars))
            return self._ensure_invocation(result)
        else:
            try:
                src = self._find_needle("files", src)
            except AnsibleError as e:
                result["failed"] = True
                result["msg"] = to_text(e)
                result["exception"] = traceback.format_exc()
                return self._ensure_invocation(result)

        changed = False
        module_return = dict(changed=False)

        # expand any user home dir specifier
        dest = self._remote_expand_user(dest)

        module_return = self._copy_file(src, os.path.basename(src), content, content_tempfile, dest, task_vars)
        if module_return is None:
            module_return = dict(changed=False, skipped=True)
            result.update(module_return)
            return self._ensure_invocation(result)

        if module_return.get("failed"):
            result.update(module_return)
            return self._ensure_invocation(result)

        if "diff" in result and not result["diff"]:
            del result["diff"]
        changed = changed or module_return.get("changed", False)

        result.update(module_return)

        # Delete tmp path
        self._remove_tmp_path(self._connection._shell.tmpdir)

        return self._ensure_invocation(result)
