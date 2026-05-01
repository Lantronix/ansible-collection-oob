from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_facts


MOCK_VERSION = {
    "model": "SLC9032",
    "current_firmware_version": "9.7.0.0R8",
    "bootloader_version": "1.0.0.0R19",
    "sw_python_version": "3.13.2",
    "sw_kernel_version": "6.6.52",
    "io_module_types": "RJ45-16, USB-16, ETH-16",
}

MOCK_STATUS = {
    "uptime": 34060479,
    "temperature": 58,
    "eth1_link": "Up",
    "eth2_link": "Up",
    "ps1": "Ok",
    "ps2": "Ok",
}

MOCK_IDENTITY = {
    "hostname": "slc9k-lab",
    "description": "Lab console server",
}


def run_module(args, check_mode=False, version_side_effect=None):
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_facts.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_facts.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_facts.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_system_version.return_value = MOCK_VERSION
                instance.get_system_status.return_value = MOCK_STATUS
                instance.get_system_identity.return_value = MOCK_IDENTITY
                if version_side_effect is not None:
                    instance.get_system_version.side_effect = version_side_effect
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_option.side_effect = lambda k: {"host": "192.0.2.1", "validate_certs": False}.get(k)
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = args
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_facts.main()
                return m, instance, mock_cls


def test_slc_facts_returns_combined_data():
    m, _client, _ = run_module({})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    facts = kwargs["slc_facts"]
    assert facts["model"] == "SLC9032"
    assert facts["current_firmware_version"] == "9.7.0.0R8"
    assert facts["uptime"] == 34060479
    assert facts["hostname"] == "slc9k-lab"


def test_slc_facts_calls_all_three_endpoints():
    _unused, client, _ = run_module({})
    client.get_system_version.assert_called_once()
    client.get_system_status.assert_called_once()
    client.get_system_identity.assert_called_once()


def test_slc_facts_api_error_calls_fail_json():
    from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError
    m, _client, _ = run_module({}, version_side_effect=AnsibleLantronixError("device unreachable"))
    m.fail_json.assert_called_once()
    assert "device unreachable" in m.fail_json.call_args[1]["msg"]


def test_slc_facts_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
