from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json
from unittest.mock import MagicMock

import pytest

from ansible_collections.lantronix.oob.plugins.cliconf.slc import Cliconf

ADMIN_VERSION = (
    b"___Current Version___\r\nModel: SLC8032\r\nFirmware Version: 9.7.0.6R4\r\n"
    b"S/N: 0080A3000001\r\nDevice ID: 00204AEXAMPLE00000000000000000001\r\n"
)


def _cliconf(responses=None):
    connection = MagicMock()
    connection.get_prompt.return_value = b"\r\n[slc8032-site1]> "
    cliconf = Cliconf(connection)
    cliconf.send_command = MagicMock(side_effect=lambda **kw: (responses or {}).get(kw["command"], b"ok"))
    return cliconf


def test_device_info():
    info = _cliconf({"admin version": ADMIN_VERSION}).get_device_info()
    assert info == {
        "network_os": "slc",
        "network_os_model": "SLC8032",
        "network_os_version": "9.7.0.6R4",
        "network_os_serial": "0080A3000001",
        "device_id": "00204AEXAMPLE00000000000000000001",
        "network_os_hostname": "slc8032-site1",
    }


def test_get_passes_prompt_and_answer():
    cliconf = _cliconf()
    cliconf.get(command="set groups delete X", prompt="Do you want", answer="yes")
    kwargs = cliconf.send_command.call_args[1]
    assert kwargs["prompt"] == "Do you want" and kwargs["answer"] == "yes"


def test_run_commands_returns_each_response():
    cliconf = _cliconf({"show groups": b"<no groups>"})
    assert cliconf.run_commands(["show groups", {"command": "show cli"}]) == [b"<no groups>", b"ok"]


def test_edit_config_runs_lines_and_skips_when_not_committing():
    cliconf = _cliconf()
    result = cliconf.edit_config(["set groups add A", "", "set groups add B"])
    assert result["request"] == ["set groups add A", "set groups add B"]
    assert len(result["response"]) == 2
    dry = _cliconf().edit_config(["set groups add A"], commit=False)
    assert dry["response"] == []


def test_get_config_not_supported():
    with pytest.raises(ValueError, match="cannot display"):
        _cliconf().get_config()


def test_capabilities():
    caps = json.loads(_cliconf({"admin version": ADMIN_VERSION}).get_capabilities())
    assert "run_commands" in caps["rpc"]
    assert caps["device_operations"]["supports_commit"] is False
