#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_users
short_description: Manage user accounts on the Percepxion platform
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates or deletes user accounts on Percepxion.
  - Checks whether the user exists before acting; only calls create or delete
    when the desired state differs from current state.
notes:
  - User management uses C(/v2/user/*) endpoints confirmed against the
    Percepxion 6.12 demo environment.
options:
  username:
    description: Username to manage.
    type: str
    required: true
  role:
    description: User role. Required when C(state=present).
    type: str
  password:
    description: User password. Required when creating a new user.
    type: str
  state:
    description: Whether the user should exist.
    type: str
    default: present
    choices: [present, absent]
"""

EXAMPLES = r"""
- name: Ensure a user exists
  lantronix.oob.percepxion_users:
    username: netops
    role: admin
    password: "{{ vault_netops_pass }}"
    state: present

- name: Remove a user
  lantronix.oob.percepxion_users:
    username: olduser
    state: absent
"""

RETURN = r"""
username:
  description: The username that was acted on.
  returned: always
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
            username=dict(type="str", required=True),
            role=dict(type="str"),
            password=dict(type="str", no_log=True),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    username = module.params["username"]
    state = module.params["state"]

    try:
        result = client.search_users(search_string=username)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    # API returns {"total": N, "result": [{id, username, ...}]}
    existing = [u["username"] for u in result.get("result", [])]
    changed = False

    if state == "present" and username not in existing:
        changed = True
        if not module.check_mode:
            try:
                client.create_user(
                    username=username,
                    role=module.params.get("role", "user"),
                    password=module.params.get("password"),
                )
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    elif state == "absent" and username in existing:
        changed = True
        if not module.check_mode:
            try:
                client.delete_user(username)
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, username=username)


if __name__ == "__main__":
    main()
