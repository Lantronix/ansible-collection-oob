#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_event_rules
short_description: Manage event rules on the Percepxion platform
version_added: "1.1.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates, updates, deletes, or lists Percepxion event rules.
  - An event rule watches a telemetry condition on a device, smart group, or all
    devices, and fires when the condition matches. Percepxion events are entirely
    rule-driven; a state change generates no event unless a rule watches it.
  - Optionally attaches email or SMS notification actions to a rule on creation.
  - Matches an existing rule by name before acting, so runs are idempotent on the
    rule's enabled state.
options:
  name:
    description: Event rule name. Rules are identified and deleted by name.
    type: str
    required: true
  state:
    description:
      - C(present) creates the rule if missing and toggles its enabled state.
      - C(absent) deletes the rule by name.
      - C(query) returns all event rules without changing anything.
    type: str
    default: present
    choices: [present, absent, query]
  enable:
    description: Whether the rule is enabled.
    type: bool
    default: true
  conditions:
    description:
      - List of condition objects defining when the rule fires. Required when
        creating a new rule.
      - Each item takes C(attr_full_name), C(attr_path), C(operator), C(new_val),
        C(old_val), and C(next_logical) (C(AND)/C(OR) between conditions).
      - Conditions are applied at create time only; changing them on an existing
        rule requires recreating it (C(state=absent) then C(state=present)).
    type: list
    elements: dict
  device_id:
    description:
      - Device keys to target. Provide exactly one of C(device_id),
        C(smart_group_id), or C(device_search).
    type: list
    elements: str
  smart_group_id:
    description: Smart group IDs to target.
    type: list
    elements: str
  device_search:
    description: Set to C('*') to target all devices instead of an explicit list.
    type: str
  app_code:
    description: Application code the rule belongs to (e.g. C(lgm)).
    type: str
  actions:
    description:
      - Notification actions to attach to the rule on creation. Each item takes
        C(action_type) (C(email) or C(sms)), C(action) (the email address or
        phone number), C(enable), and C(reminder_interval).
      - Actions are created when the rule is created. Reconciling actions on an
        already-existing rule is not handled by this module.
    type: list
    elements: dict
  project_tag:
    description: Percepxion project tag to scope the operation.
    type: str
  tenant_id:
    description: Tenant ID for Project Admin authentication.
    type: str
"""

EXAMPLES = r"""
- name: Alert when port 1 disconnects on a specific device
  lantronix.oob.percepxion_event_rules:
    name: dp-1_disconnected
    device_id:
      - EXAMPLEDEVICEKEY0000000000000001
    conditions:
      - attr_full_name: "Port 1 Status"
        attr_path: "/dgm/telemetry/port:1/status_record/dp_info/status"
        operator: changed_with_val
        new_val: "disconnected"
        old_val: "connected"
        next_logical: ""
    actions:
      - action_type: email
        action: netops@example.com
        enable: true
        reminder_interval: 0
    state: present

- name: Disable a rule without deleting it
  lantronix.oob.percepxion_event_rules:
    name: dp-1_disconnected
    enable: false
    state: present

- name: Delete a rule
  lantronix.oob.percepxion_event_rules:
    name: dp-1_disconnected
    state: absent

- name: List all event rules
  lantronix.oob.percepxion_event_rules:
    name: unused
    state: query
  register: rules
"""

RETURN = r"""
name:
  description: The rule name that was acted on.
  returned: always
  type: str
rule_id:
  description: Rule ID from Percepxion, resolved from a post-create search.
  returned: when state is present and the rule exists
  type: str
rules:
  description: All event rules, returned for state=query.
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
        host=connection.get_api_host(),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=module.params.get("project_tag") or connection.get_project_tag(),
        tenant_id=module.params.get("tenant_id") or connection.get_tenant_id(),
        verify_ssl=connection.get_option("validate_certs"),
    )


def _find_rule(client, name):
    resp = client.search_event_rules(limit=1000)
    for rule in resp.get("rules", []):
        if rule.get("name") == name:
            return rule
    return None


def main():
    module = AnsibleModule(
        argument_spec=dict(
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent", "query"]),
            enable=dict(type="bool", default=True),
            conditions=dict(type="list", elements="dict"),
            device_id=dict(type="list", elements="str"),
            smart_group_id=dict(type="list", elements="str"),
            device_search=dict(type="str"),
            app_code=dict(type="str"),
            actions=dict(type="list", elements="dict"),
        ),
        supports_check_mode=True,
        mutually_exclusive=[["device_id", "smart_group_id", "device_search"]],
    )

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    name = module.params["name"]
    state = module.params["state"]

    try:
        if state == "query":
            resp = client.search_event_rules(limit=1000)
            module.exit_json(changed=False, name=name, rules=resp.get("rules", []))

        existing = _find_rule(client, name)
        changed = False
        rule_id = existing.get("id") if existing else None

        if state == "absent":
            if existing:
                changed = True
                if not module.check_mode:
                    client.delete_event_rule(name)
            module.exit_json(changed=changed, name=name)

        # state == present
        if not existing:
            if not module.params.get("conditions"):
                module.fail_json(msg="conditions is required when creating a new event rule")
            changed = True
            if not module.check_mode:
                client.create_event_rule(
                    name=name,
                    conditions=module.params["conditions"],
                    enable=module.params["enable"],
                    device_id=module.params.get("device_id"),
                    smart_group_id=module.params.get("smart_group_id"),
                    device_search=module.params.get("device_search"),
                    app_code=module.params.get("app_code"),
                )
                created = _find_rule(client, name)
                rule_id = created.get("id") if created else None
                if module.params.get("actions"):
                    client.create_rule_action(rule_name=name, details=module.params["actions"])
        else:
            # Rule exists: reconcile enabled state (conditions are create-time only).
            if bool(existing.get("enable")) != bool(module.params["enable"]):
                changed = True
                if not module.check_mode:
                    client.update_event_rule(
                        rule_id=existing["id"],
                        name=name,
                        enable=module.params["enable"],
                    )

        result = dict(changed=changed, name=name)
        if rule_id:
            result["rule_id"] = rule_id
        module.exit_json(**result)

    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))


if __name__ == "__main__":
    main()
