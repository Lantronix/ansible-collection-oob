#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_users
short_description: Manage local user accounts on SLC 9000
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates, updates, or deletes local user accounts on an SLC 9000 device.
options:
  username:
    description: Username to manage.
    required: true
    type: str
  password:
    description: User password. Required when creating a new user (state=present).
    type: str
  role:
    description: User role.
    type: str
    choices: [admin, user, operator]
  state:
    description: Whether the user should exist.
    type: str
    default: present
    choices: [present, absent]
"""

EXAMPLES = r"""
- name: Ensure netops admin user exists
  lantronix.oob.slc_users:
    username: netops
    password: "{{ vault_netops_pass }}"
    role: admin
    state: present

- name: Remove a user
  lantronix.oob.slc_users:
    username: olduser
    state: absent
"""

RETURN = r"""
users:
  description: List of usernames present on the device after the change.
  returned: always
  type: list
  elements: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(type="str", required=True),
            password=dict(type="str", no_log=True),
            role=dict(type="str", choices=["admin", "user", "operator"]),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token(), verify_ssl=connection.get_option("validate_certs"))

    try:
        current = client.get_users()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    existing_usernames = [u["username"] for u in current.get("users", [])]
    username = module.params["username"]
    state = module.params["state"]
    changed = False

    if state == "present" and username not in existing_usernames:
        changed = True
        if not module.check_mode:
            payload = {"username": username, "role": module.params.get("role", "user")}
            if module.params.get("password"):
                payload["password"] = module.params["password"]
            try:
                client.set_users(payload)
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
            # Re-fetch after write so the returned list reflects actual device state
            try:
                updated = client.get_users()
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
            existing_usernames = [u["username"] for u in updated.get("users", [])]

    elif state == "absent" and username in existing_usernames:
        changed = True
        if not module.check_mode:
            try:
                client.set_users({"username": username, "delete": True})
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
            # Re-fetch after write so the returned list reflects actual device state
            try:
                updated = client.get_users()
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
            existing_usernames = [u["username"] for u in updated.get("users", [])]

    module.exit_json(changed=changed, users=existing_usernames)


if __name__ == "__main__":
    main()
