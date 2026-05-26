#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_audit_logs
short_description: Query audit logs from the Percepxion platform
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Returns device audit logs, user audit logs, or device access log download
    links from Percepxion. Read-only; always C(changed=False).
options:
  log_type:
    description:
      - C(device) returns platform-level device audit events.
      - C(user) returns user account audit events.
      - C(access) downloads the terminal access log for C(device_id).
    type: str
    required: true
    choices: [device, user, access]
  device_id:
    description: Device ID for access log download. Required when C(log_type=access).
    type: str
  start_time:
    description: ISO 8601 start timestamp for filtering device audit logs.
    type: str
  end_time:
    description: ISO 8601 end timestamp for filtering device audit logs.
    type: str
  limit:
    description: Maximum number of log entries to return.
    type: int
    default: 100
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
- name: Retrieve recent device audit events
  lantronix.oob.percepxion_audit_logs:
    log_type: device
    limit: 50
  register: result

- name: Retrieve user audit events in a time window
  lantronix.oob.percepxion_audit_logs:
    log_type: user
    start_time: "2026-04-01T00:00:00Z"
    end_time: "2026-04-30T23:59:59Z"

- name: Download access log for a device
  lantronix.oob.percepxion_audit_logs:
    log_type: access
    device_id: dev-001
  register: result
"""

RETURN = r"""
audit_logs:
  description: List of audit log entries. Present for C(log_type=device) and C(log_type=user).
  returned: when log_type is device or user
  type: list
  elements: dict
log_content:
  description: Raw access log text returned by the platform. Present for C(log_type=access).
  returned: when log_type is access
  type: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def _make_client(connection, module):
    tenant_id = module.params.get("tenant_id") or connection.get_tenant_id()
    project_tag = module.params.get("project_tag") or connection.get_project_tag()
    return PercepxionClient(
        host=connection.get_api_host(),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=project_tag,
        tenant_id=tenant_id,
        verify_ssl=connection.get_option("validate_certs"),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
            log_type=dict(type="str", required=True, choices=["device", "user", "access"]),
            device_id=dict(type="str"),
            start_time=dict(type="str"),
            end_time=dict(type="str"),
            limit=dict(type="int", default=100),
        ),
        required_if=[("log_type", "access", ["device_id"])],
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    log_type = module.params["log_type"]
    limit = module.params["limit"]

    if log_type == "device":
        try:
            result = client.search_audit_logs(
                start_time=module.params.get("start_time"),
                end_time=module.params.get("end_time"),
                limit=limit,
            )
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
        module.exit_json(changed=False, audit_logs=result.get("audit", []))
        return

    if log_type == "user":
        try:
            result = client.search_user_audit_logs(limit=limit)
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
        module.exit_json(changed=False, audit_logs=result.get("audit", []))
        return

    try:
        log_content = client.download_device_log(module.params["device_id"], log_level="info")
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))
    module.exit_json(changed=False, log_content=log_content or "")


if __name__ == "__main__":
    main()
