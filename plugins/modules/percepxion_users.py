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
  - Creates, deletes, suspends, or resumes user accounts on Percepxion.
  - Reads the user list first and only acts when the desired state differs from
    current state, so runs are idempotent (including on suspend/resume, which is
    checked against each user's C(enabled) flag).
notes:
  - Suspend and resume use C(PUT /v1/user) (bulk-capable) and were verified live
    against Percepxion 6.13 on 2026-08-27.
  - Delete uses C(DELETE /v1/user) (bulk by user ID). Create uses
    C(POST /v2/user/create). Validate create and delete against your target
    deployment before relying on them in production.
options:
  username:
    description: Username to manage.
    type: str
    required: true
  role:
    description: User role. Used when C(state=present) to create a new user.
    type: str
  password:
    description: User password. Used when creating a new user.
    type: str
  state:
    description:
      - C(present) creates the user if missing.
      - C(absent) deletes the user if present.
      - C(suspended) disables an existing user's access.
      - C(enabled) restores a suspended user's access.
    type: str
    default: present
    choices: [present, absent, suspended, enabled]
  project_tag:
    description:
      - Percepxion project tag to scope all operations.
      - Overrides the C(percepxion_project_tag) inventory variable when set.
    type: str
  tenant_id:
    description:
      - Percepxion tenant ID for Project Admin operations.
      - Overrides the C(percepxion_tenant_id) inventory variable when set.
    type: str
"""

EXAMPLES = r"""
- name: Ensure a user exists
  lantronix.oob.percepxion_users:
    username: netops
    role: admin
    password: "{{ vault_netops_pass }}"
    state: present

- name: Suspend a user (e.g. offboarding or incident lockdown)
  lantronix.oob.percepxion_users:
    username: contractor
    state: suspended

- name: Resume a suspended user
  lantronix.oob.percepxion_users:
    username: contractor
    state: enabled

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
        project_tag=module.params.get("project_tag") or connection.get_project_tag(),
        tenant_id=module.params.get("tenant_id") or connection.get_tenant_id(),
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
            state=dict(type="str", default="present",
                       choices=["present", "absent", "suspended", "enabled"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    username = module.params["username"]
    state = module.params["state"]

    try:
        # search_string filters on name/email; fetch and match on username exactly.
        result = client.search_users(limit=1000)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    # {"total": N, "result": [{id, username, enabled, ...}]}
    by_username = {u["username"]: u for u in result.get("result", []) if "username" in u}
    current = by_username.get(username)
    changed = False

    try:
        if state == "present":
            if current is None:
                changed = True
                if not module.check_mode:
                    client.create_user(
                        username=username,
                        role=module.params.get("role") or "user",
                        password=module.params.get("password"),
                    )

        elif state == "absent":
            if current is not None:
                changed = True
                if not module.check_mode:
                    client.delete_users([current["id"]])

        elif state in ("suspended", "enabled"):
            if current is None:
                module.fail_json(msg="cannot %s user '%s': user not found" % (state, username))
            want_enabled = (state == "enabled")
            if bool(current.get("enabled")) != want_enabled:
                changed = True
                if not module.check_mode:
                    client.set_users_enabled([current["id"]], enable=want_enabled)

    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, username=username)


if __name__ == "__main__":
    main()
