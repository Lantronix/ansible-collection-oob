from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_devices

MOCK_SEARCH = {
    "total_results": 2,
    "search_results": [
        {"device_id": "dev-001", "device_name": "slc9k-01", "status": "online"},
        {"device_id": "dev-002", "device_name": "slc9k-02", "status": "offline"},
    ],
}


def run_module(params):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_devices.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_devices.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_devices.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_devices.return_value = MOCK_SEARCH
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

                percepxion_devices.main()
                return m, instance, mock_cls


def test_list_returns_all_devices():
    m, _client, _ = run_module({"search_string": None, "limit": 100})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert len(kwargs["devices"]) == 2
    assert kwargs["total_results"] == 2


def test_search_string_passed_to_client():
    m, client, _ = run_module({"search_string": "slc9k-01", "limit": 10})
    client.search_devices.assert_called_with(search_string="slc9k-01", limit=10, offset=0)


def test_percepxion_devices_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"search_string": None, "limit": 100})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
