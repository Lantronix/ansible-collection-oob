#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_firmware
short_description: Check firmware compliance or trigger fleet firmware updates via Percepxion
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - When C(state=check), queries recent firmware job logs for the smart group
    and classifies devices as compliant or non-compliant against the target version.
    Always C(changed=False).
  - When C(state=update), creates a firmware update job group targeting the smart
    group. Always C(changed=True).
notes:
  - Firmware updates are non-idempotent. Each C(state=update) invocation creates
    a new job group regardless of current device firmware versions.
options:
  smart_group_id:
    description: Percepxion smart group ID to target.
    type: str
    required: true
  firmware_version:
    description: Target firmware version string for compliance check or update.
    type: str
    required: true
  state:
    description:
      - C(check) returns a compliance report without making changes.
      - C(update) creates a firmware update job group.
    type: str
    required: true
    choices: [check, update]
"""

EXAMPLES = r"""
- name: Check firmware compliance across a fleet group
  lantronix.oob.percepxion_firmware:
    smart_group_id: grp-001
    firmware_version: 9.7.0.0R8
    state: check
  register: result

- name: Update fleet to latest firmware
  lantronix.oob.percepxion_firmware:
    smart_group_id: grp-001
    firmware_version: 9.8.0.0R1
    state: update
"""

RETURN = r"""
compliant_devices:
  description: Devices running the target firmware version. Present when C(state=check).
  returned: when state is check
  type: list
  elements: dict
non_compliant_devices:
  description: Devices not running the target firmware version. Present when C(state=check).
  returned: when state is check
  type: list
  elements: dict
job_group_id:
  description: ID of the created firmware update job group. Present when C(state=update).
  returned: when state is update and not check_mode
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def _make_client(connection):
    return PercepxionClient(
        host=connection.get_option("host"),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=connection.get_option("percepxion_project_tag") or None,
        tenant_id=connection.get_option("percepxion_tenant_id") or None,
        verify_ssl=connection.get_option("validate_certs"),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            smart_group_id=dict(type="str", required=True),
            firmware_version=dict(type="str", required=True),
            state=dict(type="str", required=True, choices=["check", "update"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection)

    smart_group_id = module.params["smart_group_id"]
    target_version = module.params["firmware_version"]

    if module.params["state"] == "check":
        try:
            logs = client.search_job_logs(job_group_id=smart_group_id)
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))

        compliant = []
        non_compliant = []
        for entry in logs.get("job_logs", []):
            if entry.get("firmware_version") == target_version:
                compliant.append(entry)
            else:
                non_compliant.append(entry)

        module.exit_json(
            changed=False,
            compliant_devices=compliant,
            non_compliant_devices=non_compliant,
        )
        return

    job_group_id = None
    if not module.check_mode:
        try:
            result = client.create_job_group({
                "name": "firmware-update-{0}".format(smart_group_id),
                "job_type": "firmware_update",
                "smart_group_id": smart_group_id,
                "firmware_version": target_version,
            })
            job_group_id = result.get("job_group_id")
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))

    result = dict(changed=True)
    if job_group_id:
        result["job_group_id"] = job_group_id
    module.exit_json(**result)


if __name__ == "__main__":
    main()
