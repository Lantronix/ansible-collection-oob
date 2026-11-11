#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_groups
short_description: Manage custom user groups on SLC and EMG console managers over SSH
version_added: "1.5.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Ensures custom user groups exist with the given ports and rights, or are removed, on a
    Lantronix console manager (SLC 8000, SLC 9000, EMG) over an SSH CLI session.
  - Custom groups are how a console manager maps a directory group to console access. When a user
    signs in through LDAP or Active Directory and belongs to a directory group with the same name as
    a custom group, the user gets that group's ports and rights.
  - Reads the current groups first and only sends commands for groups that differ. Each host is
    handled in its own connection, so Ansible forks set how many console managers change at once.
  - Use M(lantronix.oob.percepxion_slc_groups) for console managers reachable only through Percepxion.
    Both modules take the same I(groups) definition.
notes:
  - Requires C(ansible_connection=ansible.netcommon.network_cli) and C(ansible_network_os=lantronix.oob.slc).
  - Changes apply immediately on the console manager.
  - Rights are set exactly. Rights a model does not support (for example C(sd) on models without an
    SD card) are left out for that host and reported in C(dropped_rights).
  - C(ALL) for a port option is compared against the host's full port list, so a group that already
    covers every port reports no change.
  - Check mode reads the current groups and reports the commands that would be sent.
options:
  groups:
    description:
      - Custom groups to manage. With I(state=absent) only C(name) is used.
      - Options left unset are not changed on existing groups.
    type: list
    elements: dict
    required: true
    suboptions:
      name:
        description:
          - Group name, matching the directory group name. At most 30 characters, no spaces.
          - The console manager compares names without regard to letter case.
        type: str
        required: true
      rights:
        description:
          - Exact list of two-letter user rights, for example C([sv, do]). An empty list removes all rights.
        type: list
        elements: str
      data_ports:
        description: Ports with direct access, for example C(1-32,U1,U2) or C(ALL).
        type: str
      listen_ports:
        description: Ports with listen access, for example C(ALL).
        type: str
      clear_ports:
        description: Port buffers the group may clear, for example C(ALL).
        type: str
      power_outlets:
        description: Power outlets the group may control, for example C(1-8).
        type: str
      escape_sequence:
        description: Escape sequence. Use C(\x) for non-printable characters, for example C(\x1bA).
        type: str
      break_sequence:
        description: Break sequence, for example C(\x1bB).
        type: str
      custom_menu:
        description: Name of a custom user menu that already exists on the console manager.
        type: str
      display_menu:
        description: Show the custom menu at CLI login.
        type: bool
      allow_dialback:
        description: Allow modem dial-back access.
        type: bool
      dialback_number:
        description: Dial-back phone number.
        type: str
  state:
    description: Whether the groups should exist.
    type: str
    default: present
    choices: [present, absent]
  absent_method:
    description:
      - How to remove a group when I(state=absent).
      - C(delete) deletes the group.
      - C(revoke) removes all rights and renames the group with I(revoked_prefix) so no directory
        group matches it, leaving it on the console manager. The renamed group keeps no rights and
        has dial-back turned off. Its port and power outlet lists stay, because the CLI cannot empty
        them. They grant nothing unless a directory group with the new name exists, so choose a
        I(revoked_prefix) that no directory group uses.
    type: str
    default: delete
    choices: [delete, revoke]
  revoked_prefix:
    description: Prefix for the new name of a revoked group. The result is cut to 30 characters.
    type: str
    default: revoked-
  verify:
    description: After making changes, read the groups again and fail if they do not match.
    type: bool
    default: true
"""

EXAMPLES = r"""
# Inventory for these hosts sets ansible_connection: ansible.netcommon.network_cli
# and ansible_network_os: lantronix.oob.slc.

- name: Keep directory-mapped groups identical on every console manager
  lantronix.oob.slc_groups:
    groups:
      - name: OOB-Read
        data_ports: ALL
        listen_ports: ALL
        clear_ports: ALL
        rights: [sv, do]
      - name: OOB-Admin
        data_ports: ALL
        listen_ports: ALL
        clear_ports: ALL
        rights: [ad, nt, sv, dt, lu, ra, um, dp, ub, rs, fc, dr, sn, wb, sk, do, sd, md, rp, sw]

- name: Preview changes without applying them
  lantronix.oob.slc_groups:
    groups:
      - name: OOB-Read
        rights: [sv, do, dp]
  check_mode: true

- name: Remove a group
  lantronix.oob.slc_groups:
    groups:
      - name: OOB-Contractors
    state: absent
"""

RETURN = r"""
groups:
  description: Outcome for each requested group.
  returned: always
  type: list
  elements: dict
  sample:
    - name: OOB-Read
      action: edit
      changes:
        rights: [do, sv]
      dropped_rights: []
      renamed_to: null
      commands:
        - set groups edit OOB-Read permissions do,sv,-dp
commands:
  description: Commands sent to the console manager, in order. In check mode, the commands that would be sent.
  returned: always
  type: list
  elements: str
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection, ConnectionError
from ansible_collections.lantronix.oob.plugins.module_utils import slc_groups as sg

DELETE_PROMPT = "Do you want to delete group"


class SLCCli(object):
    """Thin wrapper over the network_cli connection."""

    def __init__(self, connection):
        self.connection = connection

    def run(self, command, prompt=None, answer=None):
        """Return (output, error). error is None when the console manager accepted the command."""
        try:
            return self.connection.get(command=command, prompt=prompt, answer=answer), None
        except ConnectionError as exc:
            return "", str(exc)


def read_state(cli, need_rights, need_ports):
    """Return the parsed groups, supported rights and full port set, or raise ValueError."""
    texts = {}
    commands = ["show groups"]
    if need_rights:
        commands.append("show ldap")
    if need_ports:
        commands += ["show deviceport names", "admin version"]
    for command in commands:
        out, err = cli.run(command)
        if err:
            raise ValueError("'{0}' failed: {1}".format(command, err))
        texts[command] = out
    all_tokens = None
    if need_ports:
        all_tokens = sg.all_ports(sg.parse_port_count(texts["show deviceport names"]),
                                  sg.parse_usb_count(texts["admin version"]))
    return {
        "groups": sg.parse_show_groups(texts["show groups"]),
        "supported": sg.parse_supported_rights(texts["show ldap"]) if need_rights else set(),
        "all_ports": all_tokens,
    }


def plan(params, state):
    plans = []
    current = dict(state["groups"])
    for group in params["groups"]:
        if params["state"] == "present":
            item = sg.plan_present(group, current, state["supported"], state["all_ports"])
            item["renamed_to"] = None
        else:
            item = sg.plan_absent(group["name"], current, params["absent_method"], params["revoked_prefix"])
            item.setdefault("changes", {})
            item.setdefault("dropped_rights", [])
            if item.get("renamed_to"):
                current[item["renamed_to"].lower()] = {"name": item["renamed_to"]}
        item["name"] = group["name"]
        plans.append(item)
    return plans


def main():
    module = AnsibleModule(
        argument_spec=dict(
            groups=dict(type="list", elements="dict", required=True, options=sg.GROUP_SPEC),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            absent_method=dict(type="str", default="delete", choices=["delete", "revoke"]),
            revoked_prefix=dict(type="str", default="revoked-"),
            verify=dict(type="bool", default=True),
        ),
        supports_check_mode=True,
    )
    params = module.params
    for group in params["groups"]:
        problem = sg.validate_name(group["name"])
        if problem:
            module.fail_json(msg=problem)
            return

    present = params["state"] == "present"
    need_rights = present and any(g.get("rights") is not None for g in params["groups"])
    need_ports = present and any(
        str(g.get(opt) or "").strip().upper() == "ALL"
        for g in params["groups"] for opt in ("data_ports", "listen_ports", "clear_ports"))

    cli = SLCCli(Connection(module._socket_path))
    try:
        state = read_state(cli, need_rights, need_ports)
    except ValueError as exc:
        module.fail_json(msg=str(exc))
        return

    plans = plan(params, state)
    for item in plans:
        if item["action"] == "error":
            module.fail_json(msg="no free name to revoke group '{0}'".format(item["name"]))
            return
    commands = [c for item in plans for c in item["commands"]]
    result = dict(
        changed=bool(commands),
        commands=commands,
        groups=[dict(name=p["name"], action=p["action"], commands=p["commands"], changes=p.get("changes", {}),
                     dropped_rights=p.get("dropped_rights", []), renamed_to=p.get("renamed_to")) for p in plans],
    )
    if module.check_mode or not commands:
        module.exit_json(**result)
        return

    sent = []
    for command in commands:
        if command.startswith("set groups delete "):
            out, err = cli.run(command, prompt=DELETE_PROMPT, answer="yes")
        else:
            out, err = cli.run(command)
        sent.append(command)
        problem = err or sg.command_failed(out, None)
        if problem:
            result["commands"] = sent
            module.fail_json(msg="'{0}' failed: {1}".format(command, problem), **result)
            return

    if params["verify"]:
        try:
            after = read_state(cli, False, False)
        except ValueError as exc:
            module.fail_json(msg="changes sent, verification failed: {0}".format(exc), **result)
            return
        after["supported"] = state["supported"]
        after["all_ports"] = state["all_ports"]
        remaining = [p["name"] for p in plan(params, after) if p["commands"]]
        if remaining:
            module.fail_json(msg="groups still differ after the change: {0}".format(", ".join(remaining)), **result)
            return

    module.exit_json(**result)


if __name__ == "__main__":
    main()
