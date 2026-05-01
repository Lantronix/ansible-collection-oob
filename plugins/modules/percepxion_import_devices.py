#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_import_devices
short_description: Register and assign devices to Percepxion
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Registers one or more devices in Percepxion using POST /v1/device/register,
    then assigns them to a project.
  - Checks whether each device is already registered (by serial number) before
    calling register; skips already-registered devices.
options:
  devices:
    description: List of device descriptors to register.
    type: list
    elements: dict
    required: true
    suboptions:
      serial:
        description: Device serial number.
        type: str
        required: true
      mac:
        description: Device MAC address.
        type: str
      model:
        description: Device model string.
        type: str
  project_tag:
    description: Project to assign newly registered devices to.
    type: str
  state:
    description: Only C(present) is supported. Devices are never deleted via this module.
    type: str
    default: present
    choices: [present]
"""

EXAMPLES = r"""
- name: Register a batch of SLC 9000 devices
  lantronix.oob.percepxion_import_devices:
    devices:
      - serial: SN123456
        mac: aa:bb:cc:dd:ee:ff
        model: SLC9016
      - serial: SN789012
        mac: 11:22:33:44:55:66
        model: SLC9032
    project_tag: dc1-project
"""

RETURN = r"""
registered:
  description: List of device IDs newly registered in this run.
  returned: always
  type: list
  elements: str
skipped:
  description: List of serial numbers that were already registered and skipped.
  returned: always
  type: list
  elements: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def _make_client(connection, module):
    return PercepxionClient(
        host=connection.get_option("host"),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=module.params.get("project_tag") or None,
        tenant_id=module.params.get("tenant_id") or None,
        verify_ssl=connection.get_option("validate_certs"),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            devices=dict(type="list", elements="dict", required=True),
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
            state=dict(type="str", default="present", choices=["present"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    registered = []
    skipped = []

    for device in module.params["devices"]:
        serial = device.get("serial", "")
        try:
            existing = client.search_devices(search_string=serial)
        except AnsibleLantronixError as exc:
            module.fail_json(msg="Error searching for device {0}: {1}".format(serial, exc))

        if existing.get("total_results", 0) > 0:
            skipped.append(serial)
            continue

        if not module.check_mode:
            try:
                result = client.register_device(device)
                device_id = result.get("device_id")
                if device_id and module.params.get("project_tag"):
                    client.assign_device(device_id, project_tag=module.params["project_tag"])
                registered.append(device_id or serial)
            except AnsibleLantronixError as exc:
                module.fail_json(msg="Error registering device {0}: {1}".format(serial, exc))
        else:
            registered.append(serial)

    module.exit_json(changed=bool(registered), registered=registered, skipped=skipped)


if __name__ == "__main__":
    main()
