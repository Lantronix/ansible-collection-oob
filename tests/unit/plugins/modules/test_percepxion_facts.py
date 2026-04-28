from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_facts


MOCK_SEARCH = {
    "total_results": 42,
    "search_results": [],
    "sort_first": [],
    "sort_last": [],
}


def run_module(args, check_mode=False, side_effect=None):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_facts.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_facts.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_facts.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_devices.return_value = MOCK_SEARCH
                if side_effect is not None:
                    instance.search_devices.side_effect = side_effect
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_csrf_token.return_value = "test-csrf"
                mock_conn.get_option.return_value = None
                mock_conn._socket_path = "/tmp/fake-socket"
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = args
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_facts.main()
                return m, instance


def test_percepxion_facts_returns_device_count():
    m, _client = run_module({})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    facts = kwargs["percepxion_facts"]
    assert facts["total_devices"] == 42


def test_percepxion_facts_calls_search_devices():
    _unused, client = run_module({})
    client.search_devices.assert_called_once()


def test_percepxion_facts_api_error_calls_fail_json():
    from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError
    m, _client = run_module({}, side_effect=AnsibleLantronixError("tenant unreachable"))
    m.fail_json.assert_called_once()
    assert "tenant unreachable" in m.fail_json.call_args[1]["msg"]
