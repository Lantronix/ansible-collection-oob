#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_system
short_description: Manage system identity and reboot an SLC 9000 device
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Sets hostname and description on an SLC 9000 device via POST /system/identity.
  - Fetches current identity before writing; only applies a change when desired
    state differs from current state.
  - Optionally reboots the device. Reboot is always reported as C(changed=True)
    and is not idempotent by nature.
notes:
  - Reboot takes effect immediately and the device will be unreachable for 1-2 minutes.
    Do not combine reboot with other tasks in the same play without a C(wait_for) step.
options:
  hostname:
    description: Hostname to set on the device. Omit to leave unchanged.
    type: str
  description:
    description: Device description. Omit to leave unchanged.
    type: str
  reboot:
    description: When C(true), reboot the device after any identity changes. Always reported as changed.
    type: bool
    default: false
  state:
    description: Configuration state. Only C(present) is supported.
    type: str
    default: present
    choices: [present]
"""

EXAMPLES = r"""
- name: Set device hostname
  lantronix.oob.slc_system:
    hostname: slc9k-dc1-rack3

- name: Set hostname and description together
  lantronix.oob.slc_system:
    hostname: slc9k-dc1-rack3
    description: DC1 rack 3 console server

- name: Reboot device after maintenance
  lantronix.oob.slc_system:
    reboot: true
"""

RETURN = r"""
hostname:
  description: Hostname on the device after the task completes.
  returned: always
  type: str
  sample: slc9k-dc1-rack3
description:
  description: Description on the device after the task completes.
  returned: always
  type: str
  sample: DC1 rack 3 console server
rebooted:
  description: Whether a reboot was triggered.
  returned: always
  type: bool
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            hostname=dict(type="str"),
            description=dict(type="str"),
            reboot=dict(type="bool", default=False),
            state=dict(type="str", default="present", choices=["present"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token(), verify_ssl=connection.get_option("validate_certs"))

    try:
        current = client.get_system_identity()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    desired_hostname = module.params.get("hostname")
    desired_description = module.params.get("description")

    identity_changed = False
    if desired_hostname is not None and current.get("hostname") != desired_hostname:
        identity_changed = True
    if desired_description is not None and current.get("description") != desired_description:
        identity_changed = True

    if identity_changed and not module.check_mode:
        try:
            client.set_system_identity(
                hostname=desired_hostname,
                description=desired_description,
            )
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))

    rebooted = False
    if module.params["reboot"]:
        if not module.check_mode:
            try:
                client.reboot()
                rebooted = True
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    changed = identity_changed or module.params["reboot"]

    module.exit_json(
        changed=changed,
        hostname=desired_hostname or current.get("hostname", ""),
        description=desired_description or current.get("description", ""),
        rebooted=rebooted,
    )


if __name__ == "__main__":
    main()
