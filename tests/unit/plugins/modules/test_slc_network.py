from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_network

MOCK_INTERFACES = {
    "interfaces": [
        {
            "id": "eth1",
            "ipv4_address": "192.168.1.100",
            "netmask": "255.255.255.0",
            "dhcp": False,
        },
        {
            "id": "eth2",
            "ipv4_address": "",
            "netmask": "",
            "dhcp": True,
        },
    ]
}


def run_module(params, check_mode=False, interfaces=None):
    ifaces = interfaces if interfaces is not None else MOCK_INTERFACES
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_network.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_network.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_network.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_network_interfaces.return_value = ifaces
                instance.set_network_interfaces.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_option.return_value = "192.0.2.1"
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_network.main()
                return m, instance


def test_no_change_when_static_config_matches():
    m, client = run_module({
        "interface": "eth1",
        "ipv4_address": "192.168.1.100",
        "netmask": "255.255.255.0",
        "dhcp": False,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.set_network_interfaces.assert_not_called()


def test_changed_when_ip_differs():
    m, client = run_module({
        "interface": "eth1",
        "ipv4_address": "10.0.0.50",
        "netmask": "255.255.255.0",
        "dhcp": False,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_network_interfaces.assert_called_once()


def test_changed_when_switching_to_dhcp():
    m, client = run_module({
        "interface": "eth1",
        "ipv4_address": None,
        "netmask": None,
        "dhcp": True,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_network_interfaces.assert_called_once()


def test_no_change_when_already_dhcp():
    m, client = run_module({
        "interface": "eth2",
        "ipv4_address": None,
        "netmask": None,
        "dhcp": True,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.set_network_interfaces.assert_not_called()


def test_check_mode_blocks_write():
    m, client = run_module(
        {
            "interface": "eth1",
            "ipv4_address": "10.0.0.50",
            "netmask": "255.255.255.0",
            "dhcp": False,
            "state": "present",
        },
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_network_interfaces.assert_not_called()
