#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_smart_groups
short_description: Manage smart groups on the Percepxion platform
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates or deletes Percepxion smart groups.
  - A smart group is a dynamic device set defined by filter criteria.
  - Searches for an existing group by name before acting; skips creation if
    a group with the same name already exists.
options:
  name:
    description: Smart group name.
    type: str
    required: true
  criteria:
    description: Filter criteria dict defining group membership. Required when C(state=present).
    type: dict
  state:
    description: Whether the smart group should exist.
    type: str
    default: present
    choices: [present, absent]
"""

EXAMPLES = r"""
- name: Create a smart group for DC1 devices
  lantronix.oob.percepxion_smart_groups:
    name: dc1-servers
    criteria:
      tag: dc1
    state: present

- name: Remove a smart group
  lantronix.oob.percepxion_smart_groups:
    name: dc1-servers
    state: absent
"""

RETURN = r"""
name:
  description: Smart group name.
  returned: always
  type: str
group_id:
  description: Group ID assigned by Percepxion. Present after creation.
  returned: when changed and state is present
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
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            criteria=dict(type="dict"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection)

    name = module.params["name"]
    state = module.params["state"]

    try:
        search = client.search_smart_groups(search_string=name)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    existing = {g["name"]: g for g in search.get("search_results", [])}
    changed = False
    group_id = None

    if state == "present" and name not in existing:
        changed = True
        if not module.check_mode:
            try:
                result = client.create_smart_group(name, module.params.get("criteria") or {})
                group_id = result.get("group_id")
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    elif state == "absent" and name in existing:
        changed = True
        if not module.check_mode:
            try:
                client.delete_smart_group(existing[name]["group_id"])
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    result = dict(changed=changed, name=name)
    if group_id:
        result["group_id"] = group_id
    module.exit_json(**result)


if __name__ == "__main__":
    main()
