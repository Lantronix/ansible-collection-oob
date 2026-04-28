#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_device_ports
short_description: Query serial device port information on SLC 9000
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Returns serial port configuration from an SLC 9000 device via GET /ports.
  - Optionally fetches active port connections via GET /connections.
  - This is a read-only module. Port configuration changes are applied via
    C(slc_config) using batch CLI commands.
options:
  port_id:
    description: Filter results to a single port by its identifier (e.g. C(port1)).
      When omitted, all ports are returned.
    type: str
  gather_connections:
    description: When C(true), also return active port connections from GET /connections.
    type: bool
    default: false
"""

EXAMPLES = r"""
- name: Gather all port information
  lantronix.oob.slc_device_ports:
  register: result

- name: Inspect a single port
  lantronix.oob.slc_device_ports:
    port_id: port1
  register: result

- name: Gather ports and active connections
  lantronix.oob.slc_device_ports:
    gather_connections: true
  register: result

- name: Show active connections
  debug:
    var: result.connections
  when: result.connections is defined
"""

RETURN = r"""
ports:
  description: List of port configuration entries. Filtered to one entry when C(port_id) is set.
  returned: always
  type: list
  elements: dict
connections:
  description: List of active port connections. Only present when C(gather_connections=true).
  returned: when gather_connections is true
  type: list
  elements: dict
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            port_id=dict(type="str"),
            gather_connections=dict(type="bool", default=False),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token())

    try:
        ports_result = client.get_ports()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    ports = ports_result.get("ports", [])

    port_id = module.params.get("port_id")
    if port_id:
        ports = [p for p in ports if p.get("id") == port_id]

    result = dict(changed=False, ports=ports)

    if module.params["gather_connections"]:
        try:
            conn_result = client.get_connections()
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
        result["connections"] = conn_result.get("connections", [])

    module.exit_json(**result)


if __name__ == "__main__":
    main()
