from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock, patch

from ansible_collections.lantronix.oob.plugins.modules import percepxion_slc_groups as mod
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError

DEV = "DEV1"
GROUPS_READ = (
    "Name: OOB-Read\\n  Data Ports: 1-4\\n  Display Menu at Login: enabled\\n"
    "  Perms: Rights Allowed: sv,do\\n         Rights Denied: ad,dp\\n"
)
LDAP = "Perms: Rights Allowed: <none>\\n       Rights Denied: ad,sv,do,dp\\n"
OK = {"error": "No Error", "results": "Group settings successfully updated.\\n"}

BASE_PARAMS = dict(
    device_ids=[DEV], state="present", absent_method="revoke", revoked_prefix="revoked-",
    verify=True, job_timeout=60, poll_interval=1, request_timeout=30, project_tag=None, tenant_id=None,
)


def _group(**kw):
    group = dict((k, None) for k in mod.GROUP_SPEC)
    group.update(kw)
    return group


class FakeClient(object):
    """Simulates Percepxion CLI jobs against a single device's text state."""

    def __init__(self, groups_text, responses=None):
        self.groups_text = groups_text
        self.responses = responses or {}
        self.commands = []
        self.jobs = {}

    def create_cli_job(self, device_ids, command, name, description=""):
        job_id = "jg{0}".format(len(self.jobs) + 1)
        self.jobs[job_id] = (command, list(device_ids))
        self.commands.append(command)
        return job_id

    def search_job_states(self, job_group_id):
        return dict((d, self.job_state) for d in self.jobs[job_group_id][1])

    job_state = "Processing"

    def search_cli_results(self, job_group_id, device_ids):
        command = self.jobs[job_group_id][0]
        if command in self.responses:
            result = self.responses[command]
        elif command == "show groups":
            result = {"error": "No Error", "results": self.groups_text}
        elif command == "show ldap":
            result = {"error": "No Error", "results": LDAP}
        else:
            result = OK
        if result is None:
            return {}
        return dict((d, result) for d in device_ids)


def _run(params, client, check_mode=False):
    with patch.object(mod, "AnsibleModule") as mock_mod, \
            patch.object(mod, "Connection"), \
            patch.object(mod, "_make_client", return_value=client), \
            patch.object(mod.time, "sleep"):
        m = MagicMock()
        full = dict(BASE_PARAMS)
        full.update(params)
        m.params = full
        m.check_mode = check_mode
        mock_mod.return_value = m
        mod.main()
        return m


def test_no_change_when_group_matches():
    client = FakeClient(GROUPS_READ)
    m = _run({"groups": [_group(name="OOB-Read", rights=["sv", "do"], data_ports="1-4")]}, client)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert all(c.startswith("show") for c in client.commands)


def test_adds_missing_group_and_verifies():
    client = FakeClient("<no groups>")

    def on_create(device_ids, command, name, description=""):
        if command.startswith("set groups add"):
            client.groups_text = "Name: OOB-New\\n  Perms: Rights Allowed: sv\\n         Rights Denied: ad,do,dp\\n"
        return FakeClient.create_cli_job(client, device_ids, command, name, description)

    client.create_cli_job = on_create
    m = _run({"groups": [_group(name="OOB-New", rights=["sv"])]}, client)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    assert "set groups add OOB-New permissions sv" in client.commands
    assert kwargs["devices"][DEV]["groups"][0]["action"] == "add"
    assert client.commands.count("show groups") == 2
    assert client.commands.count("show ldap") == 1


def test_check_mode_sends_only_reads():
    client = FakeClient("<no groups>")
    m = _run({"groups": [_group(name="OOB-New", rights=["sv"])]}, client, check_mode=True)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    assert all(c.startswith("show") for c in client.commands)


def test_revoke_runs_two_steps_in_order():
    client = FakeClient(GROUPS_READ)
    params = {"groups": [_group(name="OOB-Read")], "state": "absent", "verify": False}
    m = _run(params, client)
    writes = [c for c in client.commands if not c.startswith("show")]
    assert writes == [
        "set groups edit OOB-Read permissions -do,-sv",
        "set groups rename OOB-Read newname revoked-OOB-Read",
    ]
    assert m.exit_json.call_args[1]["devices"][DEV]["groups"][0]["renamed_to"] == "revoked-OOB-Read"


def test_delete_refused_is_reported():
    refused = {"error": "command (set groups delete OOB-Read) is not permitted", "results": "No CLI results"}
    client = FakeClient(GROUPS_READ, responses={"set groups delete OOB-Read": refused})
    params = {"groups": [_group(name="OOB-Read")], "state": "absent", "absent_method": "delete"}
    m = _run(params, client)
    kwargs = m.fail_json.call_args[1]
    assert kwargs["failed_devices"] == [DEV]
    assert "not permitted" in kwargs["devices"][DEV]["error"]


def test_timeout_reported():
    client = FakeClient(GROUPS_READ, responses={"show groups": None})
    clock = iter(range(0, 1000, 30))
    with patch.object(mod.time, "time", side_effect=lambda: next(clock)):
        m = _run({"groups": [_group(name="OOB-Read", data_ports="1-4")]}, client)
    kwargs = m.fail_json.call_args[1]
    assert kwargs["timed_out"] == [DEV]


def test_completed_without_output_fails_after_grace():
    client = FakeClient(GROUPS_READ, responses={"show groups": None})
    client.job_state = "Completed"
    clock = iter(range(0, 1000, 30))
    with patch.object(mod.time, "time", side_effect=lambda: next(clock)):
        m = _run({"groups": [_group(name="OOB-Read", data_ports="1-4")], "job_timeout": 900}, client)
    kwargs = m.fail_json.call_args[1]
    assert kwargs["failed_devices"] == [DEV]
    assert "no CLI output" in kwargs["devices"][DEV]["error"]
    assert kwargs["timed_out"] == []


def test_create_error_fails_cleanly():
    client = MagicMock()
    client.create_cli_job.side_effect = AnsibleLantronixError("boom")
    m = _run({"groups": [_group(name="OOB-Read", data_ports="1-4")]}, client)
    assert "boom" in m.fail_json.call_args[1]["msg"]


def test_invalid_name_rejected():
    client = FakeClient(GROUPS_READ)
    m = _run({"groups": [_group(name="Admin")]}, client)
    assert "reserved" in m.fail_json.call_args_list[0][1]["msg"]


def test_verify_detects_drift():
    client = FakeClient(GROUPS_READ)
    m = _run({"groups": [_group(name="OOB-Read", rights=["sv"])]}, client)
    kwargs = m.fail_json.call_args[1]
    assert "still differ" in kwargs["devices"][DEV]["error"]
