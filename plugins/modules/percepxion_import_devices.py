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
  - Checks whether each device is already registered (by serial_num) before
    calling register; skips already-registered devices.
options:
  devices:
    description: List of device descriptors to register.
    type: list
    elements: dict
    required: true
    suboptions:
      serial_num:
        description:
          - Hardware serial number of the device (the manufacturer serial ID).
          - Found on the device label or via C(show px) on the SLC CLI (shown as C(S/N)).
          - Maps to the C(serial_num) field in the Percepxion v1 API.
        type: str
        required: true
      device_id:
        description:
          - The unique 32-character Percepxion Device ID assigned by Lantronix.
          - Found via C(show px) on the SLC CLI (shown as C(Device ID)).
          - Maps to the C(device_id) field in the Percepxion v1 API.
          - Required for registration; do not confuse with the hardware serial number.
        type: str
        required: true
      device_name:
        description: User-defined name for the device in Percepxion.
        type: str
        required: true
      device_description:
        description: Optional description of the device.
        type: str
      device_key:
        description:
          - Device authentication key used when the device calls home to Percepxion.
          - Leave blank for manual user-initiated imports; the device supplies this
            automatically when it registers itself.
        type: str
  project_tag:
    description: Project to assign newly registered devices to.
    type: str
  state:
    description: Only C(present) is supported. Devices are never deleted via this module.
    type: str
    default: present
    choices: [present]
  tenant_id:
    description:
      - Percepxion tenant ID for Project Admin operations.
      - Overrides the C(percepxion_tenant_id) inventory variable when set.
    type: str
"""

EXAMPLES = r"""
- name: Register SLC9000 devices in Percepxion
  lantronix.oob.percepxion_import_devices:
    devices:
      - serial_num: "SN123456"
        device_id: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4"
        device_name: "slc-datacenter-01"
    project_tag: dc1-project

# To find serial_num and device_id, run on the SLC CLI:
#   show px
# Output includes:
#   S/N: SN123456              <- use as serial_num
#   Device ID: a1b2c3d4...    <- use as device_id (32 chars)
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
        host=connection.get_api_host(),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=module.params.get("project_tag") or connection.get_project_tag(),
        tenant_id=module.params.get("tenant_id") or connection.get_tenant_id(),
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
        serial = device.get("serial_num", "")
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
