#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_config
short_description: Manage running configuration on SLC 9000
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Provides four configuration actions on an SLC 9000 device.
  - C(get) retrieves the current running configuration as CLI commands. Read-only.
  - C(compare) shows a diff between running and saved configuration. Read-only.
  - C(save) persists running configuration to flash. Always C(changed=True).
  - C(batch) executes a list of CLI configuration commands. Always C(changed=True).
notes:
  - C(save) and C(batch) are non-idempotent. Each invocation counts as a change
    regardless of whether the resulting configuration differs.
  - Use C(get) before C(batch) to inspect current state if idempotency matters
    for your use case.
options:
  action:
    description: Configuration action to perform.
    type: str
    required: true
    choices: [get, compare, save, batch]
  commands:
    description: List of CLI configuration commands to execute. Required when C(action=batch).
    type: list
    elements: str
"""

EXAMPLES = r"""
- name: Retrieve current running configuration
  lantronix.oob.slc_config:
    action: get
  register: result

- name: Show diff between running and saved config
  lantronix.oob.slc_config:
    action: compare
  register: result

- name: Save running configuration to flash
  lantronix.oob.slc_config:
    action: save

- name: Apply a set of configuration commands
  lantronix.oob.slc_config:
    action: batch
    commands:
      - set hostname slc9k-dc1
      - set ntp server 10.0.0.1
      - set logging host 10.0.0.2
"""

RETURN = r"""
commands:
  description: Running configuration as a list of CLI commands. Present when C(action=get).
  returned: when action is get
  type: list
  elements: str
diff:
  description: Diff output between running and saved configuration. Present when C(action=compare).
  returned: when action is compare
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            action=dict(type="str", required=True, choices=["get", "compare", "save", "batch"]),
            commands=dict(type="list", elements="str"),
        ),
        required_if=[("action", "batch", ["commands"])],
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token(), verify_ssl=connection.get_option("validate_certs"))

    action = module.params["action"]

    if action == "get":
        try:
            result = client.get_config_commands()
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
        module.exit_json(changed=False, commands=result.get("commands", []))
        return

    if action == "compare":
        try:
            result = client.compare_config()
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
        module.exit_json(changed=False, diff=result.get("diff", ""))
        return

    if action == "save":
        if not module.check_mode:
            try:
                client.save_config()
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
        module.exit_json(changed=True)
        return

    if not module.check_mode:
        try:
            client.post_config_batch(module.params["commands"])
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
    module.exit_json(changed=True)


if __name__ == "__main__":
    main()
