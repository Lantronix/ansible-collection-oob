from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_firmware

MOCK_VERSION = {
    "current_firmware_version": "9.7.0.0R8",
    "alternate_firmware_version": "9.6.0.0R5",
    "active_bank": "bank1",
}

MOCK_UPDATE_STATUS = {
    "status": "idle",
    "progress": 0,
}


def run_module(params, check_mode=False):
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_firmware.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_firmware.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_firmware.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_firmware_version.return_value = MOCK_VERSION
                instance.get_firmware_update_status.return_value = MOCK_UPDATE_STATUS
                instance.trigger_firmware_update.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_option.side_effect = lambda k: {"host": "192.0.2.1", "validate_certs": False}.get(k)
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_firmware.main()
                return m, instance, mock_cls


def test_check_returns_version_unchanged():
    m, client, _ = run_module({"state": "check", "url": None, "bank": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert kwargs["firmware"]["current_firmware_version"] == "9.7.0.0R8"
    assert kwargs["firmware"]["update_status"] == "idle"
    client.trigger_firmware_update.assert_not_called()


def test_update_triggers_client_call():
    m, client, _ = run_module({
        "state": "update",
        "url": "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
        "bank": None,
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.trigger_firmware_update.assert_called_once_with(
        "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin", bank=None
    )


def test_update_with_bank_passes_bank():
    m, client, _ = run_module({
        "state": "update",
        "url": "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
        "bank": "alternate",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.trigger_firmware_update.assert_called_once_with(
        "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin", bank="alternate"
    )


def test_check_mode_blocks_update():
    m, client, _ = run_module(
        {
            "state": "update",
            "url": "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
            "bank": None,
        },
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.trigger_firmware_update.assert_not_called()


def test_slc_firmware_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"state": "check", "url": None, "bank": "alternate"})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
