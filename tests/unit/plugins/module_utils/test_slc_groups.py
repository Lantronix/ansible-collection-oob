from __future__ import absolute_import, division, print_function
__metaclass__ = type

from ansible_collections.lantronix.oob.plugins.module_utils import slc_groups as sg

# Output as returned by Percepxion: line breaks escaped as backslash-n.
SHOW_GROUPS = (
    "___Current Groups Settings_____________________________________________________\\n"
    "Name: OOB-Read\\n  Data Ports: 1-32,U1,U2\\n  Listen Ports: 1-32,U1,U2\\n"
    "  Clear Ports: <none>\\n  Power Outlets: <none>\\n  Escape Sequence: \\x1bA\\n"
    "  Break Sequence: \\x1bB\\n  Custom Menu:  <none>\\n  Display Menu at Login: enabled\\n"
    "  Allow Dial-back: disabled\\n  Dial-back Number: <none>\\n"
    "  Perms: Rights Allowed: sv,do\\n         Rights Denied: ad,nt,dt,lu,ra,um,dp,ub,rs,fc,dr,sn,wb,sk,po,sd,md,rp,sw\\n"
    "Name: OOB-Admin\\n  Data Ports: 1-4\\n  Perms: Rights Allowed: <none>\\n"
)
SHOW_LDAP_SLC9 = (
    "Group: Default Users\\nPerms: Rights Allowed: <none>\\n"
    "       Rights Denied: ad,nt,sv,dt,lu,ra,um,dp,ub,rs,fc,dr,sn,wb,sk,po,do,md,rp,sw\\n"
)
DEVICEPORT_SLC8 = (
    "___Current Device Port Names___\n 01 - Port-01                        17 - Port-17\n"
    " 16 - Port-16                        32 - Port-32\n"
)
DEVICEPORT_SLC9 = "01- slc9032-site4             09- Port-09\n08- Port-08                        16- Port-16\n"
SYSCONFIG = "Model:                     SLC8032      Power Supply: AC\nNumber of USB Ports:             2      Internal Modem:\n"
SLC8_RIGHTS = set("ad,nt,sv,dt,lu,ra,um,dp,ub,rs,fc,dr,sn,wb,sk,po,do,sd,md,rp,sw".split(","))
SLC9_RIGHTS = SLC8_RIGHTS - {"sd"}


def test_parse_show_groups():
    groups = sg.parse_show_groups(SHOW_GROUPS)
    assert set(groups) == {"oob-read", "oob-admin"}
    read = groups["oob-read"]
    assert read["name"] == "OOB-Read"
    assert read["data_ports"] == "1-32,U1,U2"
    assert read["clear_ports"] == ""
    assert read["escape_sequence"] == "\\x1bA"
    assert read["display_menu"] is True
    assert read["allow_dialback"] is False
    assert read["rights"] == ["sv", "do"]
    assert groups["oob-admin"]["rights"] == []


def test_parse_empty_groups():
    assert sg.parse_show_groups("___Current Groups Settings___\\n<no groups>\\n") == {}


def test_supported_rights_slc9_has_no_sd():
    assert sg.parse_supported_rights(SHOW_LDAP_SLC9) == SLC9_RIGHTS


def test_port_counts_both_layouts():
    assert sg.parse_port_count(DEVICEPORT_SLC8) == 32
    assert sg.parse_port_count(DEVICEPORT_SLC9) == 16
    assert sg.parse_usb_count(SYSCONFIG) == 2


def test_port_set_all_and_ranges():
    full = sg.all_ports(32, 2)
    assert sg.port_set("ALL", full) == full
    assert sg.port_set("1-32,U1,U2", full) == full
    assert sg.port_set("<none>", full) == frozenset()
    assert sg.port_set("ALL", None) is None


def test_validate_name():
    assert sg.validate_name("OOB-Read") is None
    assert "reserved" in sg.validate_name("Admin")
    assert "30" in sg.validate_name("x" * 31)
    assert "spaces" in sg.validate_name("OOB Read")


def test_plan_add_new_group():
    plan = sg.plan_present({"name": "OOB-New", "data_ports": "ALL", "rights": ["sv", "do"]},
                           {}, SLC8_RIGHTS, sg.all_ports(32, 2))
    assert plan["action"] == "add"
    assert plan["commands"] == ["set groups add OOB-New dataports ALL permissions do,sv"]


def test_plan_no_change_with_all_ports():
    current = sg.parse_show_groups(SHOW_GROUPS)
    plan = sg.plan_present({"name": "oob-read", "data_ports": "ALL", "listen_ports": "ALL", "rights": ["do", "sv"]},
                           current, SLC8_RIGHTS, sg.all_ports(32, 2))
    assert plan["action"] == "none"
    assert plan["commands"] == []


def test_plan_edit_rights_removes_extra():
    current = sg.parse_show_groups(SHOW_GROUPS)
    plan = sg.plan_present({"name": "OOB-Read", "rights": ["sv"]}, current, SLC8_RIGHTS, None)
    assert plan["action"] == "edit"
    assert plan["commands"] == ["set groups edit OOB-Read permissions sv,-do"]
    assert plan["changes"] == {"rights": ["sv"]}


def test_plan_drops_unsupported_rights():
    plan = sg.plan_present({"name": "OOB-New", "rights": ["sv", "sd"]}, {}, SLC9_RIGHTS, None)
    assert plan["dropped_rights"] == ["sd"]
    assert plan["commands"] == ["set groups add OOB-New permissions sv"]


def test_plan_bool_and_text_edit():
    current = sg.parse_show_groups(SHOW_GROUPS)
    plan = sg.plan_present({"name": "OOB-Read", "display_menu": False, "escape_sequence": "\\x1bA"},
                           current, SLC8_RIGHTS, None)
    assert plan["commands"] == ["set groups edit OOB-Read displaymenu disable"]


def test_plan_absent_revoke():
    current = sg.parse_show_groups(SHOW_GROUPS)
    plan = sg.plan_absent("oob-read", current, "revoke", "revoked-")
    assert plan["action"] == "revoke"
    assert plan["commands"] == [
        "set groups edit OOB-Read permissions -do,-sv",
        "set groups rename OOB-Read newname revoked-oob-read",
    ]


def test_plan_absent_revoke_without_rights_only_renames():
    current = sg.parse_show_groups(SHOW_GROUPS)
    plan = sg.plan_absent("OOB-Admin", current, "revoke", "revoked-")
    assert plan["commands"] == ["set groups rename OOB-Admin newname revoked-OOB-Admin"]


def test_plan_absent_missing_and_delete():
    current = sg.parse_show_groups(SHOW_GROUPS)
    assert sg.plan_absent("nope", current, "revoke", "revoked-")["action"] == "none"
    assert sg.plan_absent("OOB-Read", current, "delete", "x")["commands"] == ["set groups delete OOB-Read"]


def test_tombstone_name_truncates_and_avoids_collision():
    name = "A" * 28
    current = {("revoked-" + name)[:30].lower(): {}}
    result = sg.tombstone_name(name, "revoked-", current)
    assert len(result) <= 30
    assert result.endswith("-2")


def test_command_failed():
    assert sg.command_failed("Group settings successfully updated.\\n", "No Error") is None
    assert "not permitted" in sg.command_failed("No CLI results", "command (x) is not permitted")
    assert "already exists" in sg.command_failed("Invalid group: 'x' (group already exists).", "No Error")
