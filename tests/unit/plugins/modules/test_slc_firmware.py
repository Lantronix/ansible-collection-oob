from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_firmware

MOCK_STATUS = {
    "current_firmware_version": "9.7.0.0R8",
    "alternate_firmware_version": "9.6.0.0R5",
    "current_boot_bank": "1",
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
                instance.get_firmware_status.return_value = MOCK_STATUS
                instance.get_firmware_update_status.return_value = MOCK_UPDATE_STATUS
                instance.trigger_firmware_update.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                _conn_opts = {"host": "192.168.100.75", "validate_certs": False}
                mock_conn.get_option.side_effect = _conn_opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_firmware.main()
                return m, instance, mock_cls


def test_check_returns_version_unchanged():
    m, client, mock_cls = run_module({"state": "check", "url": None, "md5_key": None, "reboot_after_update": False, "description": ""})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert kwargs["firmware"]["current_firmware_version"] == "9.7.0.0R8"
    assert kwargs["firmware"]["update_status"] == "idle"
    client.trigger_firmware_update.assert_not_called()


def test_update_triggers_client_call():
    m, client, mock_cls = run_module({
        "state": "update",
        "url": "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
        "md5_key": "abc123",
        "reboot_after_update": False,
        "description": "",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.trigger_firmware_update.assert_called_once_with(
        file_url="https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
        md5_key="abc123",
        reboot_after_update=False,
        description="",
    )


def test_update_with_bank_passes_bank():
    m, client, mock_cls = run_module({
        "state": "update",
        "url": "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
        "md5_key": "def456",
        "reboot_after_update": True,
        "description": "test update",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.trigger_firmware_update.assert_called_once_with(
        file_url="https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
        md5_key="def456",
        reboot_after_update=True,
        description="test update",
    )


def test_check_mode_blocks_update():
    m, client, mock_cls = run_module(
        {
            "state": "update",
            "url": "https://downloads.lantronix.com/firmware/9.8.0.0R1.bin",
            "md5_key": "abc123",
            "reboot_after_update": False,
            "description": "",
        },
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.trigger_firmware_update.assert_not_called()


def test_slc_firmware_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"state": "check", "url": None, "md5_key": None, "reboot_after_update": False, "description": ""})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
