#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_users
short_description: Manage the sysadmin account on SLC9000
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Returns sysadmin account attributes from the SLC9000.
  - Optionally changes the sysadmin password.
  - The SLC9000 REST API (v2) exposes only the sysadmin account; other local
    users must be managed via CLI or config/batch.
notes:
  - Requires C(ansible_network_os=lantronix.oob.slc9).
  - Password changes always report C(changed=true) because the API provides no
    way to verify whether the supplied password matches the current one.
options:
  new_password:
    description:
      - New password to set for the sysadmin account.
      - Omit to perform a read-only query of the account attributes.
    type: str
"""

EXAMPLES = r"""
- name: Get sysadmin account attributes
  lantronix.oob.slc_users:
  register: result

- name: Change sysadmin password
  lantronix.oob.slc_users:
    new_password: "{{ vault_sysadmin_pass }}"

- name: Change sysadmin password (check mode)
  lantronix.oob.slc_users:
    new_password: "{{ vault_sysadmin_pass }}"
  check_mode: true
"""

RETURN = r"""
sysadmin:
  description: Current sysadmin account attributes from the device.
  returned: always
  type: dict
  contains:
    username:
      description: Login name.
      type: str
      sample: sysadmin
    group:
      description: Group membership.
      type: str
      sample: Administrators
    permissions:
      description: Comma-separated permission codes.
      type: str
      sample: ad,nt,sv
    status:
      description: Account status (Active, Locked).
      type: str
      sample: Active
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            new_password=dict(type="str", no_log=True),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(
        host=connection.get_option("host"),
        token=connection.get_token(),
        verify_ssl=connection.get_option("validate_certs"),
    )

    try:
        sysadmin = client.get_sysadmin()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    new_password = module.params.get("new_password")
    changed = False

    if new_password:
        changed = True
        if not module.check_mode:
            try:
                client.set_sysadmin_password(new_password)
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, sysadmin=sysadmin)


if __name__ == "__main__":
    main()
