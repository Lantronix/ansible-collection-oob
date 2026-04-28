#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_devices
short_description: Query device inventory from Percepxion
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Returns a list of devices from the Percepxion platform.
  - Scoped to C(percepxion_project_tag) when set in inventory.
options:
  search_string:
    description: Filter devices by name or identifier substring.
    type: str
  limit:
    description: Maximum number of devices to return.
    type: int
    default: 100
"""

EXAMPLES = r"""
- name: List all devices in project
  lantronix.oob.percepxion_devices:
  register: result

- name: Find devices by name prefix
  lantronix.oob.percepxion_devices:
    search_string: slc9k-dc1
    limit: 50
  register: result

- name: Show total device count
  debug:
    msg: "Fleet size: {{ result.total_results }}"
"""

RETURN = r"""
devices:
  description: List of matching devices.
  returned: always
  type: list
  elements: dict
total_results:
  description: Total device count matching the query (may exceed C(limit)).
  returned: always
  type: int
  sample: 42
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            search_string=dict(type="str"),
            limit=dict(type="int", default=100),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = PercepxionClient(
        host=connection.get_option("host"),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=connection.get_option("percepxion_project_tag") or None,
        tenant_id=connection.get_option("percepxion_tenant_id") or None,
    )

    try:
        result = client.search_devices(
            search_string=module.params.get("search_string"),
            limit=module.params["limit"],
            offset=0,
        )
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(
        changed=False,
        devices=result.get("search_results", []),
        total_results=result.get("total_results", 0),
    )


if __name__ == "__main__":
    main()
