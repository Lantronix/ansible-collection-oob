from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock

import pytest

from ansible.inventory.data import InventoryData
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar

try:  # ansible-core 2.19+ renders only templates marked as trusted
    from ansible.template import trust_as_template
except ImportError:
    def trust_as_template(value):
        return value
from ansible_collections.lantronix.oob.plugins.inventory import percepxion as inv

SLC8 = {
    "device_id": "DEV-SLC8", "device_name": "slc8032-site1", "serial_num": "0080A3000001",
    "dev_type": "ltrx_itm", "status": "Connected", "project_tag": "PT",
    "tenant": [{"id": "t1", "name": "Example-Org"}],
    "attributes": {"model": "SLC8032", "firmware_ver": "9.7.0.6R4", "ipaddress": "192.0.2.73"},
}
SLC9 = {
    "device_id": "DEV-SLC9", "device_name": "slc9016-site2", "dev_type": "ltrx_itm", "status": "Connected",
    "attributes": {"model": "SLC9016", "eth1_ipv4address": "192.0.2.76"},
}
EMG_OFFLINE = {
    "device_id": "DEV-EMG", "device_name": "emg-site3", "dev_type": "ltrx_itm", "status": "Disconnected",
    "attributes": {"model": "EMG751000", "ipaddress": "192.0.2.10"},
}
GATEWAY = {
    "device_id": "DEV-G526", "device_name": "G526", "dev_type": "ltrx", "status": "Connected",
    "attributes": {"model": "G526", "ipaddress": "192.0.2.4"},
}

DEFAULTS = {
    "families": [], "connected_only": False, "hostname_source": "device_name",
    "address_attributes": ["ipaddress", "eth1_ipv4address", "eth2_ipv4address"],
    "strict": False, "compose": {}, "groups": {}, "keyed_groups": [],
    "search_string": "*", "page_size": 2, "tenant_id": None,
}


def _plugin(**options):
    plugin = inv.InventoryModule()
    opts = dict(DEFAULTS)
    opts.update(options)
    plugin.get_option = lambda name: opts[name]
    plugin.inventory = InventoryData()
    return plugin


@pytest.mark.parametrize("model,family", [
    ("SLC8032", "slc8000"), ("SLC9016", "slc9000"), ("EMG751000", "emg"), ("G526", "other"), ("", "other"),
])
def test_family(model, family):
    assert inv.device_family(model) == family


def test_address_order_and_prefix_stripped():
    keys = ["ipaddress", "eth1_ipv4address"]
    assert inv.device_address({"eth1_ipv4address": "192.0.2.1/24"}, keys) == "192.0.2.1"
    assert inv.device_address({}, keys) is None


def test_populate_groups_and_vars():
    plugin = _plugin()
    plugin._populate([SLC8, SLC9, EMG_OFFLINE, GATEWAY])
    groups = plugin.inventory.groups
    assert set(groups["percepxion_console_managers"].hosts[i].name
               for i in range(len(groups["percepxion_console_managers"].hosts))) == {"slc8032-site1", "slc9016-site2", "emg-site3"}
    assert [h.name for h in groups["percepxion_slc8000"].hosts] == ["slc8032-site1"]
    assert [h.name for h in groups["percepxion_other"].hosts] == ["G526"]
    host = plugin.inventory.get_host("slc8032-site1")
    assert host.vars["ansible_host"] == "192.0.2.73"
    assert host.vars["percepxion_device_id"] == "DEV-SLC8"
    assert host.vars["percepxion_organizations"] == ["Example-Org"]
    assert plugin.inventory.get_host("slc9016-site2").vars["ansible_host"] == "192.0.2.76"


def test_filters():
    plugin = _plugin(families=["slc8000", "emg"], connected_only=True)
    plugin._populate([SLC8, SLC9, EMG_OFFLINE, GATEWAY])
    assert sorted(plugin.inventory.hosts) == ["slc8032-site1"]


def test_hostname_source_device_id():
    plugin = _plugin(hostname_source="device_id")
    plugin._populate([SLC8])
    assert "DEV-SLC8" in plugin.inventory.hosts


def test_fetch_pages_with_search_after():
    plugin = _plugin()
    pages = [
        {"search_results": [SLC8, SLC9], "sort_last": ["slc9016-site2"]},
        {"search_results": [EMG_OFFLINE], "sort_last": ["emg-site3"]},
    ]
    calls = []

    def request(path, body, headers=None):
        calls.append((path, body))
        if path == "/v2/user/login":
            return {"token": "t", "csrf_token": "c"}
        return pages.pop(0)

    plugin._request = MagicMock(side_effect=request)
    plugin.get_option = lambda name, opts=dict(DEFAULTS, username="u", password="p"): opts[name]
    devices = plugin._fetch_devices()
    assert [d["device_id"] for d in devices] == ["DEV-SLC8", "DEV-SLC9", "DEV-EMG"]
    assert calls[2][1]["search_after"] == ["slc9016-site2"]
    assert calls[2][1]["pagination"] == "next"


def test_login_without_token_fails():
    plugin = _plugin()
    plugin._request = MagicMock(return_value={})
    plugin.get_option = lambda name, opts=dict(DEFAULTS, username="u", password="p"): opts[name]
    with pytest.raises(inv.AnsibleError, match="no token"):
        plugin._fetch_devices()


def test_verify_file_requires_suffix(tmp_path):
    good = tmp_path / "site.percepxion.yml"
    bad = tmp_path / "hosts.yml"
    good.write_text("plugin: lantronix.oob.percepxion\n")
    bad.write_text("all: {}\n")
    plugin = inv.InventoryModule()
    assert plugin.verify_file(str(good))
    assert not plugin.verify_file(str(bad))


def test_api_values_are_never_templated():
    evil = dict(SLC8, device_name="{{ lookup('pipe', 'id') }}",
                attributes=dict(SLC8["attributes"], firmware_ver="{{ 7 * 7 }}"))
    plugin = _plugin()
    plugin._populate([evil])
    (name,) = plugin.inventory.hosts
    assert "{" not in name and "'" not in name and " " not in name
    host_vars = plugin.inventory.get_host(name).vars
    templar = Templar(loader=DataLoader(), variables=host_vars)
    assert templar.template(trust_as_template("{{ percepxion_device_name }}")) == "{{ lookup('pipe', 'id') }}"
    assert templar.template(trust_as_template("{{ percepxion_firmware }}")) == "{{ 7 * 7 }}"


def test_invalid_address_not_used():
    keys = ["ipaddress", "eth1_ipv4address"]
    assert inv.device_address({"ipaddress": "bad host;rm", "eth1_ipv4address": "192.0.2.9"}, keys) == "192.0.2.9"
    assert inv.device_address({"ipaddress": "{{ x }}"}, keys) is None
    assert inv.device_address({"ipaddress": "slc.example.com"}, keys) == "slc.example.com"
    assert inv.device_address({"ipaddress": "2001:db8::1/64"}, keys) == "2001:db8::1"


def test_duplicate_names_made_unique():
    other = dict(SLC9, device_name="slc8032-site1")
    plugin = _plugin()
    plugin._populate([SLC8, other])
    assert sorted(plugin.inventory.hosts) == ["slc8032-site1", "slc8032-site1_DEV-SLC9"]


def test_name_falls_back_to_device_id():
    plugin = _plugin()
    plugin._populate([dict(SLC8, device_name="{{}}")])
    assert list(plugin.inventory.hosts) == ["DEV-SLC8"]
