#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_jobs
short_description: Manage scheduled job groups on Percepxion
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates, enables/disables, or deletes Percepxion job groups.
  - C(state=query) returns job logs for a named group without making changes.
options:
  name:
    description: Job group name.
    type: str
    required: true
  job_type:
    description: Job type identifier. Required when C(state=present) and creating a new group.
    type: str
  enabled:
    description: Whether the job group should be enabled.
    type: bool
    default: true
  state:
    description:
      - C(present) ensures the job group exists and has the desired enabled state.
      - C(absent) deletes the job group.
      - C(query) returns job logs without making changes.
    type: str
    default: present
    choices: [present, absent, query]
"""

EXAMPLES = r"""
- name: Create a nightly backup job
  lantronix.oob.percepxion_jobs:
    name: nightly-backup
    job_type: backup
    enabled: true

- name: Disable a job group
  lantronix.oob.percepxion_jobs:
    name: nightly-backup
    enabled: false

- name: Query recent job logs
  lantronix.oob.percepxion_jobs:
    name: nightly-backup
    state: query
  register: result
"""

RETURN = r"""
job_group_id:
  description: Job group ID.
  returned: when state is present or absent
  type: str
job_logs:
  description: Recent job log entries. Present when C(state=query).
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
        host=connection.get_option("host"),
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
            job_type=dict(type="str"),
            enabled=dict(type="bool", default=True),
            state=dict(type="str", default="present", choices=["present", "absent", "query"]),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    name = module.params["name"]
    state = module.params["state"]

    try:
        search = client.search_job_groups(search_string=name)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    existing = {g["name"]: g for g in search.get("search_results", [])}

    if state == "query":
        group = existing.get(name, {})
        logs = []
        if group:
            try:
                result = client.search_job_logs(job_group_id=group.get("job_group_id"))
                logs = result.get("job_logs", [])
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
        module.exit_json(changed=False, job_logs=logs)
        return

    if state == "absent":
        if name not in existing:
            module.exit_json(changed=False)
            return
        if not module.check_mode:
            try:
                client.delete_job_group(existing[name]["job_group_id"])
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
        module.exit_json(changed=True, job_group_id=existing[name]["job_group_id"])
        return

    desired_enabled = module.params["enabled"]

    if name not in existing:
        if not module.check_mode:
            try:
                result = client.create_job_group({
                    "name": name,
                    "job_type": module.params.get("job_type", ""),
                    "enabled": desired_enabled,
                })
                module.exit_json(changed=True, job_group_id=result.get("job_group_id"))
                return
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
        module.exit_json(changed=True)
        return

    group = existing[name]
    if group.get("enabled") != desired_enabled:
        if not module.check_mode:
            try:
                client.enable_job_groups([group["job_group_id"]], enabled=desired_enabled)
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
        module.exit_json(changed=True, job_group_id=group["job_group_id"])
        return

    module.exit_json(changed=False, job_group_id=group["job_group_id"])


if __name__ == "__main__":
    main()
