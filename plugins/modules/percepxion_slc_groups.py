#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: percepxion_slc_groups
short_description: Manage custom user groups on SLC and EMG console managers through Percepxion
version_added: "1.5.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Ensures custom user groups exist with the given ports and rights, or are removed, on a set of
    Lantronix console managers (SLC 8000, SLC 9000, EMG) managed by Percepxion.
  - Custom groups are how an SLC maps a directory group to console access. When a user signs in
    through LDAP or Active Directory and belongs to a directory group with the same name as a
    custom group, the user gets that group's ports and rights. Keeping the groups identical on every
    console manager keeps directory-based access consistent across the fleet.
  - Works through Percepxion CLI command jobs, so it needs no direct network path from the
    controller to the console managers. Reads the current groups first and only sends commands
    for groups that differ.
  - Each Percepxion CLI job runs asynchronously, and a device runs its jobs one at a time, so
    each command costs about a minute per step on a well-connected device. A run that sets
    rights and C(ALL) ports reads four commands first, then sends one step of changes and
    one verification read, about six minutes in total. Steps run on all devices in parallel,
    so fleet size adds little time. The module waits up to I(job_timeout) seconds for every
    device in each step. See the notes for what happens on a timeout.
notes:
  - Requires C(ansible_network_os=lantronix.oob.percepxion).
  - Check mode still sends read-only C(show) commands as Percepxion jobs to discover current state.
    It never sends a change.
  - Rights are set exactly. Rights a device model does not support (for example C(sd) on models
    without an SD card) are left out for that device and reported in C(dropped_rights).
  - C(ALL) for a port option is compared against each device's full port list, so a group that
    already covers every port reports no change.
  - Removal with I(absent_method=revoke) removes every right from the group and renames it with
    I(revoked_prefix), so the directory group no longer matches it. Users of that directory group then
    get the default remote-user access configured on the device, the same result as deleting the
    group. The renamed group stays on the device with no rights.
  - Removal with I(absent_method=delete) deletes the group. Percepxion CLI jobs refuse this command
    today, so the module reports those devices as failed and suggests I(absent_method=revoke).
  - The module needs each device to return CLI output to Percepxion. A device whose job finishes
    without output is reported as failed about a minute later, since its groups cannot be read.
  - A device that does not report within I(job_timeout) is listed in C(timed_out). Its job stays
    queued in Percepxion and can still run when the device reconnects. Run the module again later
    to confirm the final state.
options:
  device_ids:
    description:
      - Percepxion device IDs of the console managers to manage.
    type: list
    elements: str
    required: true
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
          - The device compares names without regard to letter case.
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
        description: Name of a custom user menu that already exists on the device.
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
      - C(revoke) removes all rights and renames the group so no directory group matches it.
      - C(delete) deletes the group. See the notes for current Percepxion behavior.
    type: str
    default: revoke
    choices: [revoke, delete]
  revoked_prefix:
    description: Prefix for the new name of a revoked group. The result is cut to 30 characters.
    type: str
    default: revoked-
  verify:
    description: After making changes, read the groups again and fail if any device does not match.
    type: bool
    default: true
  job_timeout:
    description:
      - Seconds to wait for every device to report back from each Percepxion job step.
      - A run makes one read step, one or two change steps and one verify step, each bounded by this value.
      - Raise it for sites on slow or intermittent links.
    type: int
    default: 900
  poll_interval:
    description: Seconds between checks for job results.
    type: int
    default: 15
  request_timeout:
    description: Seconds to wait for each Percepxion API request before treating it as failed.
    type: int
    default: 60
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
- name: Keep directory-mapped groups identical on every console manager
  lantronix.oob.percepxion_slc_groups:
    device_ids: "{{ slc_device_ids }}"
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
  register: groups_result

- name: Preview changes without applying them
  lantronix.oob.percepxion_slc_groups:
    device_ids: "{{ slc_device_ids }}"
    groups:
      - name: OOB-Read
        rights: [sv, do, dp]
  check_mode: true

- name: Revoke a group everywhere
  lantronix.oob.percepxion_slc_groups:
    device_ids: "{{ slc_device_ids }}"
    groups:
      - name: OOB-Contractors
    state: absent

- name: Allow more time for sites on cellular links
  lantronix.oob.percepxion_slc_groups:
    device_ids: "{{ remote_site_device_ids }}"
    groups:
      - name: OOB-Read
        rights: [sv, do]
    job_timeout: 1800
    poll_interval: 30
"""

RETURN = r"""
devices:
  description: Per-device outcome, keyed by Percepxion device ID.
  returned: always
  type: dict
  sample:
    00204AEXAMPLE00000000000000000002:
      status: changed
      error: null
      groups:
        - name: OOB-Read
          action: edit
          changes:
            rights: [do, sv]
          dropped_rights: []
          renamed_to: null
          commands:
            - set groups edit OOB-Read permissions do,sv,-dp
failed_devices:
  description: Device IDs where a read, change or verification failed.
  returned: always
  type: list
  elements: str
timed_out:
  description: Device IDs that did not report back within I(job_timeout) in some step.
  returned: always
  type: list
  elements: str
job_group_ids:
  description: Percepxion job group IDs created by this run, in order.
  returned: always
  type: list
  elements: str
"""

import time

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError
from ansible_collections.lantronix.oob.plugins.module_utils import slc_groups as sg

JOB_DESCRIPTION = "lantronix.oob.percepxion_slc_groups"
MAX_POLL_ERRORS = 5
# Seconds to keep waiting for CLI output after a device's job reports a final state.
RESULT_GRACE = 60
TERMINAL_STATES = ("completed", "failed", "failure", "error", "cancelled", "canceled", "expired", "timeout")
GROUP_SPEC = sg.GROUP_SPEC


def _make_client(connection, module):
    return PercepxionClient(
        host=connection.get_api_host(),
        token=connection.get_token(),
        csrf_token=connection.get_csrf_token(),
        project_tag=module.params.get("project_tag") or connection.get_project_tag(),
        tenant_id=module.params.get("tenant_id") or connection.get_tenant_id(),
        verify_ssl=connection.get_option("validate_certs"),
        timeout=module.params["request_timeout"],
    )


class JobRunner(object):
    """Runs a step of CLI commands as Percepxion jobs and waits for every device."""

    def __init__(self, client, job_timeout, poll_interval, sleep=None, clock=None):
        self.client = client
        self.job_timeout = job_timeout
        self.poll_interval = poll_interval
        self.sleep = sleep or time.sleep
        self.clock = clock or time.time
        self.job_group_ids = []
        self.warnings = []

    def run(self, commands):
        """commands: {command: [device_ids]}.

        Returns {(command, device_id): {"error", "results"} or None on timeout}.
        Raises AnsibleLantronixError when a job cannot be created.
        """
        pending = {}
        for command, devices in commands.items():
            name = "slc_groups_{0}_{1}".format(int(self.clock()), len(self.job_group_ids) + 1)
            job_group_id = self.client.create_cli_job(devices, command, name, JOB_DESCRIPTION)
            self.job_group_ids.append(job_group_id)
            pending[job_group_id] = (command, set(devices))

        outcome = {}
        deadline = self.clock() + self.job_timeout
        finished_at = {}
        errors = 0
        while pending:
            for job_group_id in list(pending):
                command, devices = pending[job_group_id]
                try:
                    found = self.client.search_cli_results(job_group_id, sorted(devices))
                    states = self.client.search_job_states(job_group_id) if len(found) < len(devices) else {}
                    errors = 0
                except AnsibleLantronixError as exc:
                    errors += 1
                    if errors >= MAX_POLL_ERRORS:
                        raise
                    self.warnings.append("retrying result check after error: {0}".format(exc))
                    continue
                for device_id, result in found.items():
                    if device_id in devices:
                        outcome[(command, device_id)] = result
                        devices.discard(device_id)
                # A job the device finished without sending CLI output back.
                now = self.clock()
                for device_id in list(devices):
                    job_state = str(states.get(device_id) or "")
                    if job_state.lower() not in TERMINAL_STATES:
                        continue
                    first = finished_at.setdefault((job_group_id, device_id), now)
                    if now - first >= RESULT_GRACE:
                        outcome[(command, device_id)] = {
                            "error": "job {0} on the device but no CLI output was returned to Percepxion".format(
                                job_state.lower()),
                            "results": "",
                        }
                        devices.discard(device_id)
                if not devices:
                    del pending[job_group_id]
            if not pending:
                break
            if self.clock() >= deadline:
                for command, devices in pending.values():
                    for device_id in devices:
                        outcome[(command, device_id)] = None
                break
            self.sleep(self.poll_interval)
        return outcome


def _read_state(runner, device_ids, need_rights, need_ports, known=None):
    """Read groups (and, when needed, supported rights and port lists) from every device.

    known: state from an earlier read; its rights and port facts are reused so
    only 'show groups' is sent again.
    """
    if known:
        need_rights = need_ports = False
    commands = {"show groups": list(device_ids)}
    if need_rights:
        commands["show ldap"] = list(device_ids)
    if need_ports:
        commands["show deviceport names"] = list(device_ids)
        commands["show sysconfig"] = list(device_ids)
    outcome = runner.run(commands)

    state, failed, timed_out = {}, {}, set()
    for device_id in device_ids:
        texts = {}
        for command in commands:
            result = outcome.get((command, device_id))
            if result is None:
                timed_out.add(device_id)
                break
            error = (result.get("error") or "").strip()
            if error and error.lower() != "no error":
                failed[device_id] = "{0}: {1}".format(command, error)
                break
            texts[command] = sg.clean_output(result.get("results"))
        if device_id in timed_out or device_id in failed:
            continue
        all_tokens = None
        if need_ports:
            all_tokens = sg.all_ports(sg.parse_port_count(texts["show deviceport names"]),
                                      sg.parse_usb_count(texts["show sysconfig"]))
        if known and device_id in known:
            state[device_id] = dict(known[device_id], groups=sg.parse_show_groups(texts["show groups"]))
            continue
        state[device_id] = {
            "groups": sg.parse_show_groups(texts["show groups"]),
            "supported": sg.parse_supported_rights(texts["show ldap"]) if need_rights else set(),
            "all_ports": all_tokens,
        }
    return state, failed, timed_out


def _plan(params, device_state):
    """Plan every group on one device. Returns a list of group plans."""
    plans = []
    current = dict(device_state["groups"])
    for group in params["groups"]:
        if params["state"] == "present":
            plan = sg.plan_present(group, current, device_state["supported"], device_state["all_ports"])
            plan["renamed_to"] = None
        else:
            plan = sg.plan_absent(group["name"], current, params["absent_method"], params["revoked_prefix"])
            plan.setdefault("changes", {})
            plan.setdefault("dropped_rights", [])
            if plan.get("renamed_to"):
                current[plan["renamed_to"].lower()] = {"name": plan["renamed_to"]}
        plan["name"] = group["name"]
        plans.append(plan)
    return plans


def _steps(plans_by_device):
    """Group commands into ordered steps: step N holds every plan's Nth command."""
    steps = []
    for device_id, plans in plans_by_device.items():
        for plan in plans:
            for index, command in enumerate(plan["commands"]):
                while len(steps) <= index:
                    steps.append({})
                steps[index].setdefault(command, []).append(device_id)
    return steps


def main():
    module = AnsibleModule(
        argument_spec=dict(
            device_ids=dict(type="list", elements="str", required=True),
            groups=dict(type="list", elements="dict", required=True, options=GROUP_SPEC),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            absent_method=dict(type="str", default="revoke", choices=["revoke", "delete"]),
            revoked_prefix=dict(type="str", default="revoked-"),
            verify=dict(type="bool", default=True),
            job_timeout=dict(type="int", default=900),
            poll_interval=dict(type="int", default=15),
            request_timeout=dict(type="int", default=60),
            project_tag=dict(type="str"),
            tenant_id=dict(type="str"),
        ),
        supports_check_mode=True,
    )
    params = module.params
    device_ids = list(dict.fromkeys(params["device_ids"]))
    if not device_ids:
        module.fail_json(msg="device_ids must contain at least one device")
    for group in params["groups"]:
        problem = sg.validate_name(group["name"])
        if problem:
            module.fail_json(msg=problem)
    if params["job_timeout"] < 1 or params["poll_interval"] < 1 or params["request_timeout"] < 1:
        module.fail_json(msg="job_timeout, poll_interval and request_timeout must be positive")

    present = params["state"] == "present"
    need_rights = present and any(g.get("rights") is not None for g in params["groups"])
    need_ports = present and any(
        str(g.get(opt) or "").strip().upper() == "ALL"
        for g in params["groups"] for opt in ("data_ports", "listen_ports", "clear_ports"))

    connection = Connection(module._socket_path)
    client = _make_client(connection, module)
    runner = JobRunner(client, params["job_timeout"], params["poll_interval"])

    devices = dict((d, {"status": "ok", "error": None, "groups": []}) for d in device_ids)
    failed, timed_out = {}, set()

    def finish(changed, msg=None):
        for device_id, error in failed.items():
            devices[device_id]["status"] = "failed"
            devices[device_id]["error"] = error
        for device_id in timed_out:
            if device_id not in failed:
                devices[device_id]["status"] = "timed_out"
        result = dict(
            changed=changed,
            devices=devices,
            failed_devices=sorted(failed),
            timed_out=sorted(timed_out),
            job_group_ids=runner.job_group_ids,
        )
        for warning in runner.warnings:
            module.warn(warning)
        if msg or failed or timed_out:
            module.fail_json(msg=msg or "{0} device(s) failed and {1} timed out".format(
                len(failed), len(timed_out - set(failed))), **result)
        else:
            module.exit_json(**result)

    try:
        state, read_failed, read_timeouts = _read_state(runner, device_ids, need_rights, need_ports)
    except AnsibleLantronixError as exc:
        finish(False, msg=str(exc))
        return
    failed.update(read_failed)
    timed_out.update(read_timeouts)

    plans_by_device = {}
    for device_id, device_state in state.items():
        plans = _plan(params, device_state)
        for plan in plans:
            if plan["action"] == "error":
                failed[device_id] = "no free name to revoke group '{0}'".format(plan["name"])
        devices[device_id]["groups"] = [dict(
            name=p["name"], action=p["action"], commands=p["commands"], changes=p.get("changes", {}),
            dropped_rights=p.get("dropped_rights", []), renamed_to=p.get("renamed_to")) for p in plans]
        if any(p["commands"] for p in plans) and device_id not in failed:
            plans_by_device[device_id] = plans
            devices[device_id]["status"] = "changed"

    changed = bool(plans_by_device)
    if module.check_mode or not changed:
        finish(changed)
        return

    # Apply step by step; a device that fails a step skips its later steps.
    try:
        for step in _steps(plans_by_device):
            step = dict((cmd, [d for d in devs if d not in failed and d not in timed_out])
                        for cmd, devs in step.items())
            step = dict((cmd, devs) for cmd, devs in step.items() if devs)
            if not step:
                continue
            outcome = runner.run(step)
            for (command, device_id), result in outcome.items():
                if result is None:
                    timed_out.add(device_id)
                    continue
                problem = sg.command_failed(result.get("results"), result.get("error"))
                if problem:
                    failed[device_id] = "'{0}': {1}".format(command, problem)
    except AnsibleLantronixError as exc:
        finish(True, msg=str(exc))
        return

    if params["verify"]:
        targets = [d for d in plans_by_device if d not in failed and d not in timed_out]
        if targets:
            try:
                after, verify_failed, verify_timeouts = _read_state(
                    runner, targets, need_rights, need_ports, known=state)
            except AnsibleLantronixError as exc:
                finish(True, msg="changes sent, verification failed: {0}".format(exc))
                return
            failed.update(verify_failed)
            timed_out.update(verify_timeouts)
            for device_id, device_state in after.items():
                remaining = [p["name"] for p in _plan(params, device_state)
                             if p["commands"] and p["action"] != "error"]
                if remaining:
                    failed[device_id] = "groups still differ after the change: {0}".format(", ".join(remaining))

    finish(True)


if __name__ == "__main__":
    main()
