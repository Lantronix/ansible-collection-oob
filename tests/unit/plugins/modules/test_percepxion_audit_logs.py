from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_audit_logs

MOCK_DEVICE_LOGS = {"audit_logs": [{"timestamp": "2026-04-01T00:00:00Z", "action": "login", "device_id": "dev-001"}]}
MOCK_USER_LOGS = {"audit_logs": [{"timestamp": "2026-04-01T00:00:00Z", "action": "create_user", "username": "netops"}]}
MOCK_ACCESS_LOG = {"url": "https://storage/logs/dev-001.log"}


def run_module(params):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_audit_logs.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_audit_logs.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_audit_logs.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_audit_logs.return_value = MOCK_DEVICE_LOGS
                instance.search_user_audit_logs.return_value = MOCK_USER_LOGS
                instance.download_device_log.return_value = MOCK_ACCESS_LOG
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_csrf_token.return_value = "test-csrf"
                mock_conn.get_option.side_effect = lambda k: {"host": "api.consoleflow.com", "validate_certs": False, "percepxion_project_tag": None, "percepxion_tenant_id": None}.get(k)
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = False
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_audit_logs.main()
                return m, instance, mock_cls


def test_device_logs_returned():
    m, client, _ = run_module({"log_type": "device", "device_id": None, "start_time": None, "end_time": None, "limit": 100})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert len(kwargs["audit_logs"]) == 1
    client.search_audit_logs.assert_called_once()


def test_user_logs_returned():
    m, client, _ = run_module({"log_type": "user", "device_id": None, "start_time": None, "end_time": None, "limit": 100})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.search_user_audit_logs.assert_called_once()


def test_access_log_downloads_for_device():
    m, client, _ = run_module({"log_type": "access", "device_id": "dev-001", "start_time": None, "end_time": None, "limit": 100})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.download_device_log.assert_called_once_with("dev-001", log_type="access")


def test_percepxion_audit_logs_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"log_type": "device", "limit": 50, "start_time": None, "end_time": None, "device_id": None})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
