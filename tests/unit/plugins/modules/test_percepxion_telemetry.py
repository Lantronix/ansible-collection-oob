from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_telemetry

MOCK_STATS = {"stats": {"cpu": 12.5, "memory": 64.0, "temperature": 55}}
MOCK_HISTORY = {"history": [{"timestamp": "2026-04-01T00:00:00Z", "value": 55}]}


def run_module(params):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_telemetry.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_telemetry.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_telemetry.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.get_telemetry_stats.return_value = MOCK_STATS
                instance.get_telemetry_history.return_value = MOCK_HISTORY
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

                percepxion_telemetry.main()
                return m, instance


def test_returns_stats_for_device():
    m, client = run_module({
        "device_id": "dev-001",
        "metrics": ["cpu", "memory", "temperature"],
        "start_time": None,
        "end_time": None,
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert "stats" in kwargs
    client.get_telemetry_stats.assert_called_once_with("dev-001", ["cpu", "memory", "temperature"])


def test_returns_history_when_time_range_given():
    m, client = run_module({
        "device_id": "dev-001",
        "metrics": ["temperature"],
        "start_time": "2026-04-01T00:00:00Z",
        "end_time": "2026-04-02T00:00:00Z",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert "history" in kwargs
    client.get_telemetry_history.assert_called_once_with(
        "dev-001", "temperature", "2026-04-01T00:00:00Z", "2026-04-02T00:00:00Z"
    )
