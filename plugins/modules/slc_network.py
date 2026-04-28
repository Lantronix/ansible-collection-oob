#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_network
short_description: Manage ethernet interface configuration on SLC 9000
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Configures ethernet interface IP settings (static or DHCP) on an SLC 9000 device.
  - Fetches current interface config before writing; only applies a change when the
    desired state differs from the current state.
options:
  interface:
    description: Interface identifier (e.g. C(eth1), C(eth2)).
    required: true
    type: str
  ipv4_address:
    description: Static IPv4 address to assign. Required when C(dhcp=false).
    type: str
  netmask:
    description: Subnet mask for the static address. Required when C(dhcp=false).
    type: str
  dhcp:
    description: Enable DHCP on the interface. When C(true), C(ipv4_address) and C(netmask) are ignored.
    type: bool
    default: true
  state:
    description: Whether the interface configuration should be applied.
    type: str
    default: present
    choices: [present]
"""

EXAMPLES = r"""
- name: Configure eth1 with a static IP
  lantronix.oob.slc_network:
    interface: eth1
    dhcp: false
    ipv4_address: 192.168.1.100
    netmask: 255.255.255.0
    state: present

- name: Set eth2 to DHCP
  lantronix.oob.slc_network:
    interface: eth2
    dhcp: true
    state: present
"""

RETURN = r"""
interface:
  description: Name of the interface that was configured.
  returned: always
  type: str
  sample: eth1
config:
  description: Resulting interface configuration (from device response or desired state).
  returned: always
  type: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def _find_interface(interfaces, name):
    for iface in interfaces.get("interfaces", []):
        if iface.get("id") == name:
            return iface
    return None


def _config_matches(current, params):
    """Return True if current interface config already matches desired state."""
    desired_dhcp = params.get("dhcp", True)
    if current.get("dhcp") != desired_dhcp:
        return False
    if not desired_dhcp:
        if current.get("ipv4_address") != (params.get("ipv4_address") or ""):
            return False
        if current.get("netmask") != (params.get("netmask") or ""):
            return False
    return True


def main():
    module = AnsibleModule(
        argument_spec=dict(
            interface=dict(type="str", required=True),
            ipv4_address=dict(type="str"),
            netmask=dict(type="str"),
            dhcp=dict(type="bool", default=True),
            state=dict(type="str", default="present", choices=["present"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token())

    try:
        current_all = client.get_network_interfaces()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    iface_name = module.params["interface"]
    current = _find_interface(current_all, iface_name)

    if current is None:
        module.fail_json(msg="Interface '{0}' not found on device".format(iface_name))

    changed = not _config_matches(current, module.params)

    if changed and not module.check_mode:
        payload = {
            "id": iface_name,
            "dhcp": module.params["dhcp"],
        }
        if not module.params["dhcp"]:
            payload["ipv4_address"] = module.params.get("ipv4_address") or ""
            payload["netmask"] = module.params.get("netmask") or ""
        try:
            client.set_network_interfaces(payload)
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))

    result_config = {
        "id": iface_name,
        "dhcp": module.params["dhcp"],
        "ipv4_address": module.params.get("ipv4_address") or "",
        "netmask": module.params.get("netmask") or "",
    }

    module.exit_json(changed=changed, interface=iface_name, config=result_config)


if __name__ == "__main__":
    main()
