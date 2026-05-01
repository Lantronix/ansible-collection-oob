#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_aoob_session
short_description: Initiate or terminate OOB terminal sessions via Percepxion
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - C(state=present) initiates an OOB terminal session to a device and returns
    a session ID. Always C(changed=True).
  - C(state=absent) terminates an active session by ID. Always C(changed=True).
notes:
  - Session endpoint paths (C(/v3/device/connect) and C(/v3/device/disconnect))
    are not confirmed in the Percepxion 6.12 API spec. Verify with Percepxion
    engineering before use in production. Update C(percepxion_client.py) if
    paths differ.
  - Sessions are non-idempotent. Each C(state=present) opens a new connection.
options:
  device_id:
    description: Percepxion device ID to connect to. Required when C(state=present).
    type: str
  session_id:
    description: Active session ID to terminate. Required when C(state=absent).
    type: str
  state:
    description: Whether to initiate or terminate a session.
    type: str
    default: present
    choices: [present, absent]
"""

EXAMPLES = r"""
- name: Initiate an OOB session to a device
  lantronix.oob.percepxion_aoob_session:
    device_id: dev-001
    state: present
  register: result

- name: Terminate a session
  lantronix.oob.percepxion_aoob_session:
    session_id: "{{ result.session_id }}"
    state: absent
"""

RETURN = r"""
session_id:
  description: Session ID returned by Percepxion. Present when C(state=present).
  returned: when state is present and not check_mode
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
        project_tag=module.params.get("project_tag") or None,
        tenant_id=module.params.get("tenant_id") or None,
        verify_ssl=connection.get_option("validate_certs"),
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
            device_id=dict(type="str"),
            session_id=dict(type="str"),
            state=dict(type="str", default="present", choices=["present", "absent"]),
        ),
        required_if=[
            ("state", "present", ["device_id"]),
            ("state", "absent", ["session_id"]),
        ],
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    state = module.params["state"]

    if state == "present":
        session_id = None
        if not module.check_mode:
            try:
                result = client.initiate_session(module.params["device_id"])
                session_id = result.get("session_id")
            except AnsibleLantronixError as exc:
                module.fail_json(msg=str(exc))
        out = dict(changed=True)
        if session_id:
            out["session_id"] = session_id
        module.exit_json(**out)
        return

    if not module.check_mode:
        try:
            client.terminate_session(module.params["session_id"])
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
    module.exit_json(changed=True)


if __name__ == "__main__":
    main()
