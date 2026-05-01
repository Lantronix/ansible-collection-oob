from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_device_ports

MOCK_PORTS = {
    "ports": [
        {"id": "port1", "name": "Port 1", "type": "serial", "baud_rate": 9600},
        {"id": "port2", "name": "Port 2", "type": "serial", "baud_rate": 115200},
    ]
}

MOCK_CONNECTIONS = {
    "connections": [
        {"port_id": "port1", "status": "active", "user": "netops"},
    ]
}


def run_module(params, check_mode=False):
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_device_ports.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_device_ports.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_device_ports.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_ports.return_value = MOCK_PORTS
                instance.get_connections.return_value = MOCK_CONNECTIONS
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

                slc_device_ports.main()
                return m, instance, mock_cls


def test_returns_all_ports_when_no_filter():
    m, client, _ = run_module({"port_id": None, "gather_connections": False})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert len(kwargs["ports"]) == 2
    client.get_ports.assert_called_once()


def test_filters_to_single_port():
    m, client, _ = run_module({"port_id": "port1", "gather_connections": False})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert len(kwargs["ports"]) == 1
    assert kwargs["ports"][0]["id"] == "port1"


def test_includes_connections_when_requested():
    m, client, _ = run_module({"port_id": None, "gather_connections": True})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert "connections" in kwargs
    assert len(kwargs["connections"]) == 1
    client.get_connections.assert_called_once()


def test_no_connections_by_default():
    m, client, _ = run_module({"port_id": None, "gather_connections": False})
    kwargs = m.exit_json.call_args[1]
    assert "connections" not in kwargs
    client.get_connections.assert_not_called()


def test_slc_device_ports_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"port_id": None, "gather_connections": False})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
