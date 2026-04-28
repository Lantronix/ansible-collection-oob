from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_firmware

MOCK_LOGS = {
    "job_logs": [
        {"device_id": "dev-001", "device_name": "slc9k-01", "firmware_version": "9.7.0.0R8", "status": "success"},
        {"device_id": "dev-002", "device_name": "slc9k-02", "firmware_version": "9.6.0.0R5", "status": "success"},
    ]
}


def run_module(params, check_mode=False):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_firmware.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_firmware.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_firmware.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_job_logs.return_value = MOCK_LOGS
                instance.create_job_group.return_value = {"job_group_id": "jg-001"}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_csrf_token.return_value = "test-csrf"
                mock_conn.get_option.return_value = None
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_firmware.main()
                return m, instance


def test_check_returns_compliance_unchanged():
    m, client = run_module({"smart_group_id": "grp-001", "firmware_version": "9.7.0.0R8", "state": "check"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert "compliant_devices" in kwargs
    assert "non_compliant_devices" in kwargs
    client.create_job_group.assert_not_called()


def test_update_creates_job_group():
    m, client = run_module({"smart_group_id": "grp-001", "firmware_version": "9.8.0.0R1", "state": "update"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_job_group.assert_called_once()


def test_check_mode_blocks_update():
    m, client = run_module(
        {"smart_group_id": "grp-001", "firmware_version": "9.8.0.0R1", "state": "update"},
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_job_group.assert_not_called()
