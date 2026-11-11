from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import MagicMock, patch

from ansible.module_utils.connection import ConnectionError
from ansible_collections.lantronix.oob.plugins.modules import slc_groups as mod
from ansible_collections.lantronix.oob.plugins.module_utils import slc_groups as sg

READ = (
    "Name: OOB-Read\r\n  Data Ports: 1-4\r\n  Display Menu at Login: enabled\r\n"
    "  Perms: Rights Allowed: sv,do\r\n         Rights Denied: ad,dp\r\n"
)
LDAP = "Perms: Rights Allowed: <none>\r\n       Rights Denied: ad,sv,do,dp\r\n"
OK = "Group settings successfully updated.\r\n"


def _group(**kw):
    group = dict((k, None) for k in sg.GROUP_SPEC)
    group.update(kw)
    return group


class FakeConnection(object):
    def __init__(self, groups_text, after_text=None, errors=None):
        self.groups_text = groups_text
        self.after_text = after_text
        self.errors = errors or {}
        self.sent = []

    def get(self, command=None, prompt=None, answer=None):
        self.sent.append((command, prompt, answer))
        if command in self.errors:
            raise ConnectionError(self.errors[command])
        if command == "show groups":
            return self.groups_text
        if command == "show ldap":
            return LDAP
        if command.startswith("set "):
            if self.after_text is not None:
                self.groups_text = self.after_text
            return OK
        return ""


def _run(params, conn, check_mode=False):
    full = dict(state="present", absent_method="delete", revoked_prefix="revoked-", verify=True)
    full.update(params)
    with patch.object(mod, "AnsibleModule") as mock_mod, patch.object(mod, "Connection", return_value=conn):
        m = MagicMock()
        m.params = full
        m.check_mode = check_mode
        mock_mod.return_value = m
        mod.main()
        return m


def test_no_change():
    conn = FakeConnection(READ)
    m = _run({"groups": [_group(name="OOB-Read", rights=["sv", "do"], data_ports="1-4")]}, conn)
    assert m.exit_json.call_args[1]["changed"] is False
    assert all(not c[0].startswith("set ") for c in conn.sent)


def test_add_and_verify():
    added = READ + "Name: OOB-New\r\n  Perms: Rights Allowed: sv\r\n         Rights Denied: ad,do,dp\r\n"
    conn = FakeConnection(READ, after_text=added)
    m = _run({"groups": [_group(name="OOB-New", rights=["sv"])]}, conn)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    assert kwargs["commands"] == ["set groups add OOB-New permissions sv"]
    assert [c[0] for c in conn.sent].count("show ldap") == 1


def test_check_mode_sends_nothing():
    conn = FakeConnection(READ)
    m = _run({"groups": [_group(name="OOB-Read", rights=["sv"])]}, conn, check_mode=True)
    assert m.exit_json.call_args[1]["commands"] == ["set groups edit OOB-Read permissions sv,-do"]
    assert all(not c[0].startswith("set ") for c in conn.sent)


def test_delete_answers_prompt():
    conn = FakeConnection(READ, after_text="<no groups>\r\n")
    m = _run({"groups": [_group(name="oob-read")], "state": "absent"}, conn)
    assert m.exit_json.call_args[1]["commands"] == ["set groups delete OOB-Read"]
    assert ("set groups delete OOB-Read", mod.DELETE_PROMPT, "yes") in conn.sent


def test_revoke_renames():
    conn = FakeConnection(READ, after_text="Name: revoked-OOB-Read\r\n  Perms: Rights Allowed: <none>\r\n")
    m = _run({"groups": [_group(name="OOB-Read")], "state": "absent", "absent_method": "revoke"}, conn)
    assert m.exit_json.call_args[1]["commands"] == [
        "set groups edit OOB-Read permissions -do,-sv",
        "set groups rename OOB-Read newname revoked-OOB-Read",
    ]


def test_command_error_fails():
    cmd = "set groups add OOB-New permissions sv"
    conn = FakeConnection(READ, errors={cmd: "Invalid permissions 'sv'."})
    m = _run({"groups": [_group(name="OOB-New", rights=["sv"])]}, conn)
    assert "Invalid permissions" in m.fail_json.call_args[1]["msg"]


def test_read_error_fails():
    conn = FakeConnection(READ, errors={"show groups": "Unknown parameter: 'groups'"})
    m = _run({"groups": [_group(name="OOB-Read")]}, conn)
    assert "show groups" in m.fail_json.call_args[1]["msg"]


def test_verify_detects_drift():
    conn = FakeConnection(READ)
    m = _run({"groups": [_group(name="OOB-Read", rights=["sv"])]}, conn)
    assert "still differ" in m.fail_json.call_args[1]["msg"]


def test_reserved_name_rejected():
    m = _run({"groups": [_group(name="power")]}, FakeConnection(READ))
    assert "reserved" in m.fail_json.call_args[1]["msg"]
