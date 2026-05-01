#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_projects
short_description: Assign or unassign a device from a Percepxion project
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Assigns a device to a named project or removes it from its current project.
  - Fetches the device's current project assignment before acting; only calls
    assign or unassign when the state differs from the current assignment.
options:
  device_id:
    description: Percepxion device ID to manage.
    type: str
    required: true
  project_tag:
    description: Project tag to assign the device to. Required when C(state=present).
    type: str
  state:
    description: Whether the device should be assigned to C(project_tag).
    type: str
    default: present
    choices: [present, absent]
"""

EXAMPLES = r"""
- name: Assign device to a project
  lantronix.oob.percepxion_projects:
    device_id: dev-001
    project_tag: dc1-project
    state: present

- name: Remove device from its current project
  lantronix.oob.percepxion_projects:
    device_id: dev-001
    state: absent
"""

RETURN = r"""
device_id:
  description: The device ID that was acted on.
  returned: always
  type: str
project_tag:
  description: The project tag after the operation.
  returned: always
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def _make_client(connection):
    return PercepxionClient(
        host=connection.get_option("host"),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=connection.get_option("percepxion_project_tag") or None,
        tenant_id=connection.get_option("percepxion_tenant_id") or None,
        verify_ssl=connection.get_option("validate_certs"),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            device_id=dict(type="str", required=True),
            project_tag=dict(type="str"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        required_if=[("state", "present", ["project_tag"])],
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection)

    device_id = module.params["device_id"]
    desired_tag = module.params.get("project_tag")
    state = module.params["state"]

    try:
        device = client.get_device(device_id)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    current_tag = device.get("project_tag")
    changed = False

    if state == "present" and current_tag != desired_tag:
        changed = True
        if not module.check_mode:
            try:
                client.assign_device(device_id, project_tag=desired_tag)
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    elif state == "absent" and current_tag:
        changed = True
        if not module.check_mode:
            try:
                client.unassign_device(device_id)
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, device_id=device_id, project_tag=desired_tag or current_tag)


if __name__ == "__main__":
    main()
