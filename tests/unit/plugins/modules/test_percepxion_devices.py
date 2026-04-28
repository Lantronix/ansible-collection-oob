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
                mock_conn.get_option.return_value = None
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = False
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_devices.main()
                return m, instance


def test_list_returns_all_devices():
    m, _ = run_module({"search_string": None, "limit": 100})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert len(kwargs["devices"]) == 2
    assert kwargs["total_results"] == 2


def test_search_string_passed_to_client():
    m, client = run_module({"search_string": "slc9k-01", "limit": 10})
    client.search_devices.assert_called_with(search_string="slc9k-01", limit=10, offset=0)
