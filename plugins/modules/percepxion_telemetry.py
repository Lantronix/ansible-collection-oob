#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_telemetry
short_description: Query telemetry data for devices on Percepxion
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - When C(start_time) and C(end_time) are provided, returns historical telemetry
    data for a single metric over the time range.
  - When no time range is provided, returns current telemetry stats for the listed
    metrics.
  - Read-only; always C(changed=False).
notes:
  - Historical queries support only a single metric per call. When multiple metrics
    are listed and a time range is given, only the first metric is queried.
options:
  device_id:
    description: Percepxion device ID to query.
    type: str
    required: true
  metrics:
    description: List of metric names to retrieve (e.g. C(cpu), C(memory), C(temperature)).
    type: list
    elements: str
    required: true
  start_time:
    description: ISO 8601 start timestamp for historical queries.
    type: str
  end_time:
    description: ISO 8601 end timestamp for historical queries.
    type: str
"""

EXAMPLES = r"""
- name: Get current telemetry stats
  lantronix.oob.percepxion_telemetry:
    device_id: dev-001
    metrics:
      - cpu
      - memory
      - temperature
  register: result

- name: Get temperature history for past 24 hours
  lantronix.oob.percepxion_telemetry:
    device_id: dev-001
    metrics:
      - temperature
    start_time: "2026-04-27T00:00:00Z"
    end_time: "2026-04-28T00:00:00Z"
  register: result
"""

RETURN = r"""
stats:
  description: Current telemetry values keyed by metric name. Present when no time range given.
  returned: when start_time and end_time are not provided
  type: dict
history:
  description: Time-series data points for the queried metric. Present when time range given.
  returned: when start_time and end_time are provided
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
            device_id=dict(type="str", required=True),
            metrics=dict(type="list", elements="str", required=True),
            start_time=dict(type="str"),
            end_time=dict(type="str"),
        ),
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    device_id = module.params["device_id"]
    metrics = module.params["metrics"]
    start_time = module.params.get("start_time")
    end_time = module.params.get("end_time")

    if start_time and end_time:
        try:
            result = client.get_telemetry_history(device_id, metrics[0], start_time, end_time)
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
        module.exit_json(changed=False, history=result.get("history", []))
        return

    try:
        result = client.get_telemetry_stats(device_id, metrics)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))
    module.exit_json(changed=False, stats=result.get("stats", {}))


if __name__ == "__main__":
    main()
