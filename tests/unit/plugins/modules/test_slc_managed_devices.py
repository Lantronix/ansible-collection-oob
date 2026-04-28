from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_managed_devices

MOCK_MANAGED_DEVICES = {
    "managed_devices": [
        {"id": "dev1", "name": "cisco-router", "status": "managed", "port_id": "port1"},
        {"id": "dev2", "name": "juniper-switch", "status": "unmanaged", "port_id": "port2"},
        {"id": "dev3", "name": "arista-switch", "status": "discovered", "port_id": "port3"},
    ]
}


def run_module(params):
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_managed_devices.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_managed_devices.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_managed_devices.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_managed_devices.return_value = MOCK_MANAGED_DEVICES
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_option.return_value = "192.0.2.1"
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = False
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_managed_devices.main()
                return m, instance


def test_returns_all_devices_when_no_filter():
    m, client = run_module({"filter_status": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert len(kwargs["managed_devices"]) == 3
    client.get_managed_devices.assert_called_once()


def test_filters_by_status_managed():
    m, client = run_module({"filter_status": "managed"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert len(kwargs["managed_devices"]) == 1
    assert kwargs["managed_devices"][0]["name"] == "cisco-router"


def test_filters_by_status_unmanaged():
    m, client = run_module({"filter_status": "unmanaged"})
    kwargs = m.exit_json.call_args[1]
    assert len(kwargs["managed_devices"]) == 1
    assert kwargs["managed_devices"][0]["name"] == "juniper-switch"


def test_filters_by_status_discovered():
    m, client = run_module({"filter_status": "discovered"})
    kwargs = m.exit_json.call_args[1]
    assert len(kwargs["managed_devices"]) == 1
    assert kwargs["managed_devices"][0]["name"] == "arista-switch"
