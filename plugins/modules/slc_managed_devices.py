#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_managed_devices
short_description: Query devices discovered on serial ports of an SLC 9000
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Returns the list of devices discovered on SLC 9000 serial ports via GET /managed_devices.
  - Optionally filters the list by device status.
  - This is a read-only module. Device management state is controlled via the
    SLC 9000 web UI or CLI.
options:
  filter_status:
    description:
      - Filter returned devices by management status.
      - C(managed) returns only devices under active management.
      - C(unmanaged) returns devices detected but not yet managed.
      - C(discovered) returns devices in the discovery phase.
      - When omitted, all devices are returned regardless of status.
    type: str
    choices: [managed, unmanaged, discovered]
"""

EXAMPLES = r"""
- name: List all devices on serial ports
  lantronix.oob.slc_managed_devices:
  register: result

- name: List only actively managed devices
  lantronix.oob.slc_managed_devices:
    filter_status: managed
  register: result

- name: Find unmanaged devices for onboarding
  lantronix.oob.slc_managed_devices:
    filter_status: unmanaged
  register: result
"""

RETURN = r"""
managed_devices:
  description: List of devices discovered on serial ports, filtered by C(filter_status) when set.
  returned: always
  type: list
  elements: dict
  contains:
    id:
      description: Unique device identifier.
      type: str
      sample: dev1
    name:
      description: Device hostname or label.
      type: str
      sample: cisco-router
    status:
      description: Device management status (managed, unmanaged, discovered).
      type: str
      sample: managed
    port_id:
      description: Serial port the device is connected to.
      type: str
      sample: port1
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            filter_status=dict(
                type="str",
                choices=["managed", "unmanaged", "discovered"],
            ),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token(), verify_ssl=connection.get_option("validate_certs"))

    try:
        result = client.get_managed_devices()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    devices = result.get("managed_devices", [])

    filter_status = module.params.get("filter_status")
    if filter_status:
        devices = [d for d in devices if d.get("status") == filter_status]

    module.exit_json(changed=False, managed_devices=devices)


if __name__ == "__main__":
    main()
