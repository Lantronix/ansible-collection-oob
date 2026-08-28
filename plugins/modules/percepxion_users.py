#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_users
short_description: Manage user accounts on the Percepxion platform
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Creates, deletes, suspends, or resumes user accounts on Percepxion.
  - Reads the user list first and only acts when the desired state differs from
    current state, so runs are idempotent (including on suspend/resume, which is
    checked against each user's C(enabled) flag).
  - Suspend and resume can target one user (I(username)), an explicit list
    (I(usernames)), or every account except an allowlist (I(all_except)) for
    incident-lockdown workflows. Bulk operations issue a single API call.
notes:
  - Suspend and resume use C(PUT /v1/user), which accepts many users per call.
  - Delete uses C(DELETE /v1/user) (bulk by user ID). Create uses
    C(POST /v2/user/create). Validate create and delete against your target
    deployment before relying on them in production.
  - Suspending an account does not terminate sessions that user already has
    open. Pair suspension with session termination on the appliances (see the
    C(lockdown.yml) playbook shipped with this collection).
  - With I(all_except), the account this connection is authenticated as is added
    to the allowlist automatically so a lockdown cannot cut off its own operator.
    List it explicitly anyway.
options:
  username:
    description:
      - Username to manage. Required for C(state=present) and C(state=absent).
      - Exactly one of I(username), I(usernames), or I(all_except) must be set.
    type: str
  usernames:
    description:
      - List of accounts to suspend or resume. Only valid with C(state=suspended)
        or C(state=enabled).
      - Each entry is a Percepxion username (matched exactly) or an email address
        (any entry containing C(@), matched case-insensitively against the
        account's email).
    type: list
    elements: str
    version_added: "1.2.0"
  all_except:
    description:
      - Allowlist mode. Suspend every account visible to this connection except
        the ones listed. Only valid with C(state=suspended).
      - Entries follow the same username-or-email rules as I(usernames).
    type: list
    elements: str
    version_added: "1.2.0"
  role:
    description: User role. Used when C(state=present) to create a new user.
    type: str
  password:
    description: User password. Used when creating a new user.
    type: str
  state:
    description:
      - C(present) creates the user if missing.
      - C(absent) deletes the user if present.
      - C(suspended) disables an existing user's access.
      - C(enabled) restores a suspended user's access.
    type: str
    default: present
    choices: [present, absent, suspended, enabled]
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
- name: Ensure a user exists
  lantronix.oob.percepxion_users:
    username: netops
    role: admin
    password: "{{ vault_netops_pass }}"
    state: present

- name: Suspend a user (e.g. offboarding or incident lockdown)
  lantronix.oob.percepxion_users:
    username: contractor
    state: suspended

- name: Resume a suspended user
  lantronix.oob.percepxion_users:
    username: contractor
    state: enabled

- name: Remove a user
  lantronix.oob.percepxion_users:
    username: olduser
    state: absent

- name: Suspend several accounts in one call (username or email)
  lantronix.oob.percepxion_users:
    usernames:
      - contractor
      - jdoe@example.com
    state: suspended

- name: Incident lockdown, suspend everyone except break-glass accounts
  lantronix.oob.percepxion_users:
    all_except:
      - secops-breakglass
      - netops-oncall
    state: suspended
  register: lockdown

- name: Resume the accounts the lockdown suspended
  lantronix.oob.percepxion_users:
    usernames: "{{ lockdown.users | map(attribute='username') | list }}"
    state: enabled
"""

RETURN = r"""
username:
  description: The username that was acted on (single-user form).
  returned: when I(username) is set
  type: str
users:
  description: Accounts whose state was changed (or would be, in check mode).
  returned: when I(usernames) or I(all_except) is set
  type: list
  elements: dict
  sample:
    - username: contractor
      user_id: 8b0fe7c9-acbf-4d83-a011-4ad9a26eb09b
      enabled: false
skipped:
  description: Accounts that were already in the requested state.
  returned: when I(usernames) or I(all_except) is set
  type: list
  elements: str
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


def _record_email(record):
    for key in ("email", "email_address", "email_id"):
        value = record.get(key)
        if value:
            return str(value)
    return None


def _resolve_identifiers(identifiers, records, module):
    """Map usernames or email addresses to user records.

    Entries containing '@' match case-insensitively on the account email; all
    other entries match the username exactly. Fails on unknown or ambiguous
    entries. Returns an ordered {username: record} dict.
    """
    by_username = {u["username"]: u for u in records if u.get("username")}
    by_email = {}
    ambiguous = set()
    for record in records:
        email = _record_email(record)
        if not email:
            continue
        key = email.lower()
        if key in by_email:
            ambiguous.add(key)
        by_email[key] = record

    resolved = {}
    missing = []
    for ident in identifiers:
        if "@" in ident:
            key = ident.lower()
            if key in ambiguous:
                module.fail_json(msg="email %s matches more than one Percepxion account; use the username" % ident)
            record = by_email.get(key)
        else:
            record = by_username.get(ident)
        if record is None:
            missing.append(ident)
        else:
            resolved[record["username"]] = record
    if missing:
        module.fail_json(msg="user(s) not found in Percepxion: %s" % ", ".join(sorted(missing)))
    return resolved


def _bulk_enable(module, connection, client, records, state):
    """Suspend or resume a set of accounts with one PUT /v1/user call."""
    want_enabled = (state == "enabled")
    usernames = module.params.get("usernames")
    if usernames is not None:
        targets = _resolve_identifiers(usernames, records, module)
    else:
        allow = set(_resolve_identifiers(module.params["all_except"], records, module))
        try:
            operator = connection.get_option("remote_user")
        except Exception:  # option may not exist on every connection type
            operator = None
        if operator:
            allow.add(operator)
        targets = dict((u["username"], u) for u in records
                       if u.get("username") and u["username"] not in allow)

    to_write = []
    skipped = []
    for username, record in targets.items():
        if bool(record.get("enabled")) == want_enabled:
            skipped.append(username)
            continue
        to_write.append({"username": username, "user_id": record["id"], "enabled": want_enabled})

    changed = bool(to_write)
    if changed and not module.check_mode:
        client.set_users_enabled([u["user_id"] for u in to_write], enable=want_enabled)
    module.exit_json(changed=changed, users=to_write, skipped=skipped)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
            username=dict(type="str"),
            usernames=dict(type="list", elements="str"),
            all_except=dict(type="list", elements="str"),
            role=dict(type="str"),
            password=dict(type="str", no_log=True),
            state=dict(type="str", default="present",
                       choices=["present", "absent", "suspended", "enabled"]),
        ),
        mutually_exclusive=[["username", "usernames", "all_except"]],
        required_one_of=[["username", "usernames", "all_except"]],
        supports_check_mode=True,
    )

    state = module.params["state"]
    username = module.params.get("username")
    bulk = module.params.get("usernames") is not None or module.params.get("all_except") is not None

    if bulk and state not in ("suspended", "enabled"):
        module.fail_json(msg="usernames and all_except are only valid with state=suspended or state=enabled")
    if module.params.get("all_except") is not None and state != "suspended":
        module.fail_json(msg="all_except is only valid with state=suspended")

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)

    try:
        # search_string filters on name/email; fetch and match on username exactly.
        result = client.search_users(limit=1000)
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    # {"total": N, "result": [{id, username, enabled, ...}]}
    records = [u for u in result.get("result", []) if "username" in u]

    if bulk:
        try:
            _bulk_enable(module, connection, client, records, state)
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))
        return

    by_username = dict((u["username"], u) for u in records)
    current = by_username.get(username)
    changed = False

    try:
        if state == "present":
            if current is None:
                changed = True
                if not module.check_mode:
                    client.create_user(
                        username=username,
                        role=module.params.get("role") or "user",
                        password=module.params.get("password"),
                    )

        elif state == "absent":
            if current is not None:
                changed = True
                if not module.check_mode:
                    client.delete_users([current["id"]])

        elif state in ("suspended", "enabled"):
            if current is None:
                module.fail_json(msg="cannot %s user '%s': user not found" % (state, username))
            want_enabled = (state == "enabled")
            if bool(current.get("enabled")) != want_enabled:
                changed = True
                if not module.check_mode:
                    client.set_users_enabled([current["id"]], enable=want_enabled)

    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    module.exit_json(changed=changed, username=username)


if __name__ == "__main__":
    main()
