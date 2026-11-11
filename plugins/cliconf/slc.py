from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
name: slc
short_description: CLI interface for Lantronix SLC and EMG console managers
description:
  - Runs CLI commands over SSH on Lantronix SLC 8000, SLC 9000 and EMG console managers
    through the C(ansible.netcommon.network_cli) connection.
  - The console manager applies each command immediately. There is no candidate
    configuration, commit, rollback or running-configuration diff.
  - Output paging must be off for the account Ansible uses, which is the factory default.
    The connection fails with instructions if paging is on.
version_added: "1.5.0"
author:
  - Lantronix Product Team (@lantronix)
"""

EXAMPLES = r"""
- name: Run show commands on SLC console managers over SSH
  hosts: slc_ssh
  gather_facts: false
  vars:
    ansible_connection: ansible.netcommon.network_cli
    ansible_network_os: lantronix.oob.slc
  tasks:
    - name: Show custom groups
      ansible.netcommon.cli_command:
        command: show groups
      register: groups

    - name: Delete a custom group, answering the confirmation prompt
      ansible.netcommon.cli_command:
        command: set groups delete OOB-Contractors
        prompt: "Do you want to delete group"
        answer: "yes"
"""

import json
import re

from collections.abc import Mapping

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.common.text.converters import to_text
from ansible_collections.ansible.netcommon.plugins.module_utils.network.common.utils import to_list
from ansible_collections.ansible.netcommon.plugins.plugin_utils.cliconf_base import CliconfBase

VERSION_FIELDS = (
    ("network_os_model", r"^Model:\s*(\S+)"),
    ("network_os_version", r"^Firmware Version:\s*(\S+)"),
    ("network_os_serial", r"^S/N:\s*(\S+)"),
    ("device_id", r"^Device ID:\s*(\S+)"),
)
PROMPT_HOSTNAME = re.compile(r"\[([^\]\r\n]+)\]>\s*$")


class Cliconf(CliconfBase):

    def get(self, command=None, prompt=None, answer=None, sendonly=False, newline=True,
            output=None, check_all=False):
        if not command:
            raise ValueError("must provide value of command to execute")
        if output:
            raise ValueError("'output' value %s is not supported for get" % output)
        return self.send_command(command=command, prompt=prompt, answer=answer,
                                 sendonly=sendonly, newline=newline, check_all=check_all)

    def run_commands(self, commands=None, check_rc=True):
        if commands is None:
            raise ValueError("'commands' value is required")
        responses = []
        for cmd in to_list(commands):
            if not isinstance(cmd, Mapping):
                cmd = {"command": cmd}
            output = cmd.pop("output", None)
            if output:
                raise ValueError("'output' value %s is not supported for run_commands" % output)
            try:
                out = self.send_command(**cmd)
            except AnsibleConnectionFailure as exc:
                if check_rc:
                    raise
                out = getattr(exc, "err", to_text(exc))
            responses.append(out)
        return responses

    def get_config(self, source="running", flags=None, format=None):
        raise ValueError(
            "the console manager CLI cannot display its configuration; "
            "use 'admin config save' to export it to a file"
        )

    def edit_config(self, candidate=None, commit=True, replace=None, comment=None):
        """Run each line as a command. Changes apply immediately on the device."""
        if replace or comment:
            raise ValueError("replace and comment are not supported on this platform")
        requests, responses = [], []
        for line in to_list(candidate):
            if not isinstance(line, Mapping):
                line = {"command": line}
            if not line.get("command"):
                continue
            requests.append(line["command"])
            if commit:
                responses.append(self.send_command(**line))
        return {"request": requests, "response": responses}

    def get_device_info(self):
        device_info = {"network_os": "slc"}
        try:
            data = to_text(self.get(command="admin version"), errors="surrogate_or_strict")
        except AnsibleConnectionFailure:
            return device_info
        for key, pattern in VERSION_FIELDS:
            match = re.search(pattern, data, re.M)
            if match:
                device_info[key] = match.group(1)
        prompt = to_text(self._connection.get_prompt() or b"", errors="surrogate_or_strict")
        match = PROMPT_HOSTNAME.search(prompt.strip())
        if match:
            device_info["network_os_hostname"] = match.group(1)
        return device_info

    def get_device_operations(self):
        return {
            "supports_diff_replace": False,
            "supports_commit": False,
            "supports_rollback": False,
            "supports_defaults": False,
            "supports_onbox_diff": False,
            "supports_commit_comment": False,
            "supports_multiline_delimiter": False,
            "supports_diff_match": False,
            "supports_diff_ignore_lines": False,
            "supports_generate_diff": False,
            "supports_replace": False,
        }

    def get_option_values(self):
        return {"format": ["text"], "diff_match": [], "diff_replace": [], "output": []}

    def get_capabilities(self):
        result = super(Cliconf, self).get_capabilities()
        result["rpc"] += ["run_commands", "get_device_info"]
        result["device_operations"] = self.get_device_operations()
        result.update(self.get_option_values())
        return json.dumps(result)
