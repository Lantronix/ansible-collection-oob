#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_device_tags
short_description: Manage device tags on the Percepxion platform
version_added: "1.1.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates or deletes Percepxion device tags and assigns or unassigns them to devices.
  - A device tag is a named, colored label used to categorize devices.
  - Matches an existing tag by name before creating, so tag creation is idempotent.
  - Assignment calls are sent whenever C(device_ids) is provided; per-device
    assignment state is not read back, so those runs always report changed.
options:
  name:
    description: Tag name. Tags are matched and deleted by name.
    type: str
    required: true
  state:
    description:
      - C(present) ensures the tag exists; if C(device_ids) is given, assigns the tag to them.
      - C(absent) with C(device_ids) unassigns the tag from those devices, leaving the tag.
      - C(absent) without C(device_ids) deletes the tag.
      - C(query) returns all tags without changing anything.
    type: str
    default: present
    choices: [present, absent, query]
  color:
    description: Tag foreground color as a HEX string (e.g. C(#FFFFFF)). Required when creating a tag.
    type: str
  background_color:
    description: Tag background color as a HEX string (e.g. C(#1D4ED8)). Required when creating a tag.
    type: str
  device_ids:
    description: Device keys to assign the tag to (C(state=present)) or unassign it from (C(state=absent)).
    type: list
    elements: str
  project_tag:
    description: Percepxion project tag to scope the operation.
    type: str
  tenant_id:
    description: Tenant ID for Project Admin authentication.
    type: str
"""

EXAMPLES = r"""
- name: Ensure a "production" tag exists
  lantronix.oob.percepxion_device_tags:
    name: production
    color: "#FFFFFF"
    background_color: "#DC2626"
    state: present

- name: Tag two devices as production
  lantronix.oob.percepxion_device_tags:
    name: production
    color: "#FFFFFF"
    background_color: "#DC2626"
    device_ids:
      - EXAMPLEDEVICEKEY0000000000000001
      - EXAMPLEDEVICEKEY0000000000000002
    state: present

- name: Remove the production tag from one device
  lantronix.oob.percepxion_device_tags:
    name: production
    device_ids:
      - EXAMPLEDEVICEKEY0000000000000002
    state: absent

- name: Delete the production tag entirely
  lantronix.oob.percepxion_device_tags:
    name: production
    state: absent
"""

RETURN = r"""
name:
  description: The tag name that was acted on.
  returned: always
  type: str
tag_id:
  description: Tag ID from Percepxion.
  returned: when the tag exists or was created
  type: str
tags:
  description: All device tags, returned for state=query.
  returned: when state is query
  type: list
  elements: dict
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


def _find_tag(client, name):
    resp = client.list_device_tags()
    for tag in resp.get("tag", []):
        if tag.get("name") == name:
            return tag
    return None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent", "query"]),
            color=dict(type="str"),
            background_color=dict(type="str"),
            device_ids=dict(type="list", elements="str"),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    name = module.params["name"]
    state = module.params["state"]
    device_ids = module.params.get("device_ids")

    try:
        if state == "query":
            resp = client.list_device_tags()
            module.exit_json(changed=False, name=name, tags=resp.get("tag", []))

        existing = _find_tag(client, name)
        changed = False
        tag_id = existing.get("id") if existing else None

        if state == "present":
            if not existing:
                if not (module.params.get("color") and module.params.get("background_color")):
                    module.fail_json(msg="color and background_color are required to create a tag")
                changed = True
                if not module.check_mode:
                    r = client.create_device_tag(
                        name=name,
                        color=module.params["color"],
                        background_color=module.params["background_color"],
                    )
                    tag_id = r.get("id")
            if device_ids:
                changed = True
                if not module.check_mode:
                    # tag_id is None only in check_mode-before-create; guarded above
                    client.assign_device_tag(tag_ids=[tag_id], device_ids=device_ids)

        elif state == "absent":
            if existing and device_ids:
                changed = True
                if not module.check_mode:
                    client.unassign_device_tag(tag_ids=[tag_id], device_ids=device_ids)
            elif existing:
                changed = True
                if not module.check_mode:
                    client.delete_device_tag([tag_id])

        result = dict(changed=changed, name=name)
        if tag_id:
            result["tag_id"] = tag_id
        module.exit_json(**result)

    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
