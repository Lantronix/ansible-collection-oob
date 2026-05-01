from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_import_devices

ALREADY_REGISTERED = {
    "total_results": 1,
    "search_results": [{"device_id": "dev-001", "serial": "SN123456"}],
}
NOT_REGISTERED = {"total_results": 0, "search_results": []}


def run_module(params, check_mode=False, search_result=None):
    result = search_result if search_result is not None else NOT_REGISTERED
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_import_devices.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_import_devices.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_import_devices.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_devices.return_value = result
                instance.register_device.return_value = {"device_id": "dev-new"}
                instance.assign_device.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_csrf_token.return_value = "test-csrf"
                _conn_opts = {"host": "api.consoleflow.com", "validate_certs": False}
                mock_conn.get_option.side_effect = _conn_opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_import_devices.main()
                return m, instance, mock_cls


DEVICES = [{"serial": "SN123456", "mac": "aa:bb:cc:dd:ee:ff", "model": "SLC9016"}]


def test_registers_new_device():
    m, client, mock_cls = run_module({"devices": DEVICES, "project_tag": "dc1", "state": "present"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.register_device.assert_called_once()


def test_skips_already_registered_device():
    m, client, mock_cls = run_module(
        {"devices": DEVICES, "project_tag": "dc1", "state": "present"},
        search_result=ALREADY_REGISTERED,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.register_device.assert_not_called()


def test_check_mode_blocks_register():
    m, client, mock_cls = run_module(
        {"devices": DEVICES, "project_tag": "dc1", "state": "present"},
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.register_device.assert_not_called()


def test_percepxion_import_devices_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"devices": [], "project_tag": None})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
