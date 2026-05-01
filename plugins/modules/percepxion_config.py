#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_config
short_description: Manage configuration content objects on Percepxion
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates, updates, or deletes configuration content objects (config files,
    scripts, certificates) stored in Percepxion.
  - Searches for existing content by name before acting; skips creation if
    content with the same name already exists.
options:
  name:
    description: Content object name.
    type: str
    required: true
  content_type:
    description: Type of content. Required when C(state=present).
    type: str
    choices: [config, script, certificate]
  data:
    description: Content body as a string. Required when C(state=present).
    type: str
  state:
    description: Whether the content object should exist.
    type: str
    default: present
    choices: [present, absent]
"""

EXAMPLES = r"""
- name: Push a baseline config template
  lantronix.oob.percepxion_config:
    name: baseline-config
    content_type: config
    data: "{{ lookup('file', 'templates/baseline.cfg') }}"
    state: present

- name: Remove a config object
  lantronix.oob.percepxion_config:
    name: old-config
    state: absent
"""

RETURN = r"""
name:
  description: Content object name.
  returned: always
  type: str
content_id:
  description: Percepxion content ID. Present after creation.
  returned: when changed and state is present
  type: str
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
            content_type=dict(type="str", choices=["config", "script", "certificate"]),
            data=dict(type="str"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    name = module.params["name"]
    state = module.params["state"]

    try:
        search = client.search_content()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    # API returns {"total": N, "result": [{id, name, type, ...}]}
    existing = {c["name"]: c for c in search.get("result", [])}
    changed = False
    content_id = None

    if state == "present" and name not in existing:
        changed = True
        if not module.check_mode:
            try:
                result = client.create_content(
                    name, module.params.get("content_type", "config"), module.params.get("data", "")
                )
                content_id = result.get("id")
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    elif state == "absent" and name in existing:
        changed = True
        if not module.check_mode:
            try:
                client.delete_content(existing[name]["id"])
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    result = dict(changed=changed, name=name)
    if content_id:
        result["content_id"] = content_id
    module.exit_json(**result)


if __name__ == "__main__":
    main()
