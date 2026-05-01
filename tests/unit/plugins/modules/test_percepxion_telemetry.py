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
                _conn_opts = {"host": "api.consoleflow.com", "validate_certs": False}
                mock_conn.get_option.side_effect = _conn_opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = False
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_telemetry.main()
                return m, instance, mock_cls


def test_returns_stats_for_device():
    m, client, mock_cls = run_module({
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
    m, client, mock_cls = run_module({
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


def test_percepxion_telemetry_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"device_id": "dev-001", "metrics": ["cpu"], "start_time": None, "end_time": None})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
