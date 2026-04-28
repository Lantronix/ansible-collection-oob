#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_facts
short_description: Gather facts from a Percepxion platform tenant
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Returns device count and summary information for the connected Percepxion tenant.
  - Scoped to the project defined by C(percepxion_project_tag) inventory variable when set.
notes:
  - Requires C(ansible_network_os=lantronix.oob.percepxion) and
    C(ansible_connection=ansible.netcommon.httpapi).
"""

EXAMPLES = r"""
- name: Gather Percepxion platform facts
  lantronix.oob.percepxion_facts:
  register: result

- name: Show total managed devices
  ansible.builtin.debug:
    msg: "Devices in fleet: {{ result.percepxion_facts.total_devices }}"
"""

RETURN = r"""
percepxion_facts:
  description: Summary information about the Percepxion tenant.
  returned: always
  type: dict
  contains:
    total_devices:
      description: Total number of devices visible in the current project scope.
      type: int
      sample: 42
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(argument_spec={}, supports_check_mode=True)

    connection = Connection(module._socket_path)
    token = connection.get_token()
    csrf = connection.get_csrf_token()
    host = connection.get_option("host")
    project_tag = connection.get_option("percepxion_project_tag") or None
    tenant_id = connection.get_option("percepxion_tenant_id") or None

    client = PercepxionClient(
        host=host, token=token, csrf_token=csrf,
        project_tag=project_tag, tenant_id=tenant_id,
    )

    try:
        search_result = client.search_devices(limit=1)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))
        return

    facts = {"total_devices": search_result.get("total_results", 0)}
    module.exit_json(changed=False, percepxion_facts=facts)


if __name__ == "__main__":
    main()
