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
  query_string:
    description:
      - Filter expression defining group membership (e.g. C(device_name:SLC*)).
      - Required when C(state=present) unless C(device_ids) is provided.
    type: str
  device_ids:
    description:
      - List of device IDs to include in the smart group.
      - Used instead of C(query_string) for static group membership.
    type: list
    elements: str
  project_tag:
    description: Percepxion project tag to scope the operation.
    type: str
  tenant_id:
    description: Tenant ID for Project Admin authentication.
    type: str
  state:
    description: Whether the smart group should exist.
    type: str
    default: present
    choices: [present, absent]
"""

EXAMPLES = r"""
- name: Create a smart group matching SLC devices
  lantronix.oob.percepxion_smart_groups:
    name: slc-devices
    query_string: "device_name:SLC*"
    state: present

- name: Remove a smart group
  lantronix.oob.percepxion_smart_groups:
    name: slc-devices
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
  sample: ebcc77ae-b0f7-417e-b699-f63929d81ac2
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
        project_tag=module.params.get("project_tag") or None,
        tenant_id=module.params.get("tenant_id") or None,
        verify_ssl=connection.get_option("validate_certs"),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
            name=dict(type="str", required=True),
            query_string=dict(type="str"),
            device_ids=dict(type="list", elements="str"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    name = module.params["name"]
    state = module.params["state"]

    try:
        search = client.search_smart_groups(search_string=name)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    # API returns search_result (list); each item has id and name fields
    existing = {g["name"]: g for g in search.get("search_result", [])}
    changed = False
    group_id = None

    if state == "present" and name not in existing:
        changed = True
        if not module.check_mode:
            try:
                result = client.create_smart_group(
                    name,
                    query_string=module.params.get("query_string"),
                    device_ids=module.params.get("device_ids"),
                )
                group_id = result.get("id")
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    elif state == "absent" and name in existing:
        changed = True
        if not module.check_mode:
            try:
                client.delete_smart_group(existing[name]["id"])
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    result = dict(changed=changed, name=name)
    if group_id:
        result["group_id"] = group_id
    module.exit_json(**result)


if __name__ == "__main__":
    main()
