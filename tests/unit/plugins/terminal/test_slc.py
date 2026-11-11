from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock

import pytest

from ansible.errors import AnsibleConnectionFailure
from ansible_collections.lantronix.oob.plugins.terminal.slc import TerminalModule


def _matches(patterns, data):
    return any(p.search(data) for p in patterns)


@pytest.mark.parametrize("prompt", [b"\r\n[slc8032-site1]> ", b"[slc9016-site2]> ", b"\n[emg-site3]>"])
def test_prompt_matches_all_models(prompt):
    assert _matches(TerminalModule.terminal_stdout_re, prompt)


def test_prompt_ignores_bracketed_values_in_output():
    assert not _matches(TerminalModule.terminal_stdout_re, b"Default Gateway:            [none]\r\n")


@pytest.mark.parametrize("error", [
    b"show nonsense\r\nUnknown parameter: 'nonsense'\r\n",
    b"set groups add\r\nMissing value for parameter 'add'.\r\n",
    b"Invalid group: 'x' (group already exists).\r\n",
    b"Invalid dataports: 1-48 (please specify ...)\r\n",
    b"Invalid permissions 'sv,di'.\r\n",
    b"Error: cannot obtain script permissions.\r\n",
])
def test_errors_detected(error):
    assert _matches(TerminalModule.terminal_stderr_re, error)


@pytest.mark.parametrize("output", [
    b"Group settings successfully updated.\r\n",
    b"Perms: Rights Allowed: sv,do\r\n         Rights Denied: ad,nt\r\n",
    b"Fail-over GW Failed Pings:      10\r\n",
])
def test_normal_output_not_an_error(output):
    assert not _matches(TerminalModule.terminal_stderr_re, output)


def _terminal(show_cli):
    terminal = TerminalModule(MagicMock())
    terminal._exec_cli_command = MagicMock(return_value=show_cli)
    return terminal


def test_open_shell_accepts_paging_disabled_text_or_bytes():
    _terminal("Number of terminal lines: disabled\r\n").on_open_shell()
    _terminal(b"Number of terminal lines: disabled\r\n").on_open_shell()


def test_open_shell_refuses_paging():
    with pytest.raises(AnsibleConnectionFailure, match="set cli terminallines disable"):
        _terminal("Number of terminal lines: 24\r\n").on_open_shell()
