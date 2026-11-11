from __future__ import absolute_import, division, print_function
__metaclass__ = type

import re

from ansible.errors import AnsibleConnectionFailure
from ansible.module_utils.common.text.converters import to_bytes
from ansible_collections.ansible.netcommon.plugins.plugin_utils.terminal_base import TerminalBase

# Lantronix SLC 8000, SLC 9000 and EMG console managers.
# Prompt is the hostname in brackets: "[slc8032-site1]> ".
PAGING_ON = re.compile(rb"Number of terminal lines:\s*(\d+)")


class TerminalModule(TerminalBase):
    terminal_stdout_re = [
        re.compile(rb"[\r\n]?\[[^\]\r\n]+\]> ?$"),
    ]

    terminal_stderr_re = [
        re.compile(rb"(?m)^Unknown parameter: "),
        re.compile(rb"(?m)^Missing value for parameter "),
        re.compile(rb"(?m)^Invalid [A-Za-z -]+: "),
        re.compile(rb"(?m)^Invalid permissions "),
        re.compile(rb"(?m)^Error: "),
    ]

    def on_open_shell(self):
        """Refuse sessions that page output.

        Factory default is no paging. Paging is a saved per-user setting on the
        device, so it is reported rather than changed silently.
        """
        try:
            out = self._exec_cli_command(b"show cli")
        except AnsibleConnectionFailure:
            return
        match = PAGING_ON.search(to_bytes(out or b"", errors="surrogate_or_strict"))
        if match:
            raise AnsibleConnectionFailure(
                "Output paging is set to {0} lines for this account. Run "
                "'set cli terminallines disable' for the automation account "
                "on the device, then retry.".format(match.group(1).decode())
            )
