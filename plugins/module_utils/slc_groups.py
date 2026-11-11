from __future__ import absolute_import, division, print_function
__metaclass__ = type

# Parsing and planning helpers for SLC custom groups managed through
# Percepxion CLI command jobs. Pure functions, no I/O.

import re

MAX_NAME_LENGTH = 30
RESERVED_NAMES = ("admin", "power", "default")

# Module option name -> (CLI parameter, "Show groups" label, kind)
ATTRIBUTES = (
    ("data_ports", "dataports", "Data Ports", "ports"),
    ("listen_ports", "listenports", "Listen Ports", "ports"),
    ("clear_ports", "clearports", "Clear Ports", "ports"),
    ("power_outlets", "accessoutlets", "Power Outlets", "outlets"),
    ("escape_sequence", "escapeseq", "Escape Sequence", "text"),
    ("break_sequence", "breakseq", "Break Sequence", "text"),
    ("custom_menu", "custommenu", "Custom Menu", "text"),
    ("display_menu", "displaymenu", "Display Menu at Login", "bool"),
    ("allow_dialback", "allowdialback", "Allow Dial-back", "bool"),
    ("dialback_number", "dialbacknumber", "Dial-back Number", "text"),
)

PORT_TOKEN = re.compile(r"^(\d+)(?:-(\d+))?$")
NAME_LINE = re.compile(r"^\s*Name:\s*(\S.*?)\s*$")
FIELD_LINE = re.compile(r"^\s*([A-Za-z][A-Za-z \-]*?):\s*(.*?)\s*$")
RIGHTS_ALLOWED = re.compile(r"Rights Allowed:\s*(\S.*?)\s*$", re.M)
RIGHTS_DENIED = re.compile(r"Rights Denied:\s*(\S.*?)\s*$", re.M)
DEVICEPORT_NUMBER = re.compile(r"(?:^|\s)(\d{1,3})\s?-\s")
USB_COUNT = re.compile(r"Number of USB Ports:\s*(\d+)")
SUCCESS_TEXT = "successfully updated"


def clean_output(text):
    """Turn a CLI result string into plain text lines.

    Percepxion returns CLI output with line breaks escaped as the two
    characters backslash and n. Escape sequence values such as \\x1bA are
    left untouched.
    """
    if text is None:
        return ""
    text = str(text)
    return text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\t", "\t").replace("\r", "")


def _none(value):
    value = (value or "").strip()
    return "" if value in ("<none>", "none") else value


def _rights_list(value):
    value = _none(value)
    if not value:
        return []
    return [r.strip() for r in value.split(",") if r.strip()]


def parse_show_groups(text):
    """Parse 'show groups' output into {lower_name: attrs}."""
    groups = {}
    current = None
    for line in clean_output(text).split("\n"):
        match = NAME_LINE.match(line)
        if match:
            current = {"name": match.group(1), "rights": []}
            groups[current["name"].lower()] = current
            continue
        if current is None:
            continue
        allowed = RIGHTS_ALLOWED.search(line)
        if allowed:
            current["rights"] = _rights_list(allowed.group(1))
            continue
        field = FIELD_LINE.match(line)
        if not field:
            continue
        label, value = field.group(1).strip(), field.group(2)
        for option, dummy, show_label, kind in ATTRIBUTES:
            if label == show_label:
                if kind == "bool":
                    current[option] = value.strip().lower() == "enabled"
                else:
                    current[option] = _none(value)
                break
    return groups


def parse_supported_rights(text):
    """All rights a device knows, from the Perms lines of 'show ldap'."""
    text = clean_output(text)
    rights = set()
    for pattern in (RIGHTS_ALLOWED, RIGHTS_DENIED):
        for match in pattern.finditer(text):
            rights.update(_rights_list(match.group(1)))
    return rights


def parse_port_count(text):
    numbers = [int(n) for n in DEVICEPORT_NUMBER.findall(clean_output(text))]
    return max(numbers) if numbers else 0


def parse_usb_count(text):
    match = USB_COUNT.search(clean_output(text))
    return int(match.group(1)) if match else 0


def all_ports(port_count, usb_count):
    tokens = set(str(n) for n in range(1, port_count + 1))
    tokens.update("U{0}".format(n) for n in range(1, usb_count + 1))
    return frozenset(tokens)


def port_set(value, all_tokens=None):
    """Expand a port list ('1-4,6,U1', 'ALL', '<none>') into a set of tokens.

    Returns None when the value is ALL and the device's full list is unknown.
    """
    value = _none(value)
    if not value:
        return frozenset()
    if value.strip().upper() == "ALL":
        return all_tokens
    tokens = set()
    for part in value.split(","):
        part = part.strip()
        match = PORT_TOKEN.match(part)
        if match:
            start = int(match.group(1))
            end = int(match.group(2) or start)
            tokens.update(str(n) for n in range(start, end + 1))
        elif part:
            tokens.add(part.upper())
    return frozenset(tokens)


def validate_name(name):
    """Return an error string, or None when the group name is usable."""
    if not name or re.search(r"\s", name):
        return "group name '{0}' must be non-empty and contain no spaces".format(name)
    if len(name) > MAX_NAME_LENGTH:
        return "group name '{0}' exceeds {1} characters".format(name, MAX_NAME_LENGTH)
    if name.lower() in RESERVED_NAMES:
        return "group name '{0}' is reserved on the device".format(name)
    return None


def _cli_value(kind, value):
    if kind == "bool":
        return "enable" if value else "disable"
    value = str(value)
    return value if value else '""'


def _differs(kind, desired, current, all_tokens):
    if kind == "bool":
        return bool(desired) != bool(current)
    if kind == "ports":
        want = port_set(desired, all_tokens)
        have = port_set(current, all_tokens)
        if want is None:
            return True
        return want != have
    return _none(str(desired)) != _none(current)


def rights_argument(desired, supported, current=None):
    """Build a permissions argument that leaves exactly the desired rights.

    The device treats the permission list as changes to the current rights,
    so every other supported right is removed explicitly.
    """
    desired = [r for r in desired if r in supported]
    removals = sorted(r for r in supported if r not in desired)
    if current is not None:
        removals = sorted(r for r in removals if r in current)
    parts = sorted(desired) + ["-" + r for r in removals]
    return ",".join(parts)


def plan_present(group, current, supported, all_tokens):
    """Plan one desired group on one device.

    Returns a dict with action (none|add|edit), command, changes and
    dropped_rights.
    """
    name = group["name"]
    existing = current.get(name.lower())
    desired_rights = group.get("rights")
    dropped = []
    if desired_rights is not None:
        dropped = sorted(r for r in desired_rights if r not in supported)
        desired_rights = [r for r in desired_rights if r in supported]

    changes = {}
    params = []
    for option, cli_param, dummy, kind in ATTRIBUTES:
        value = group.get(option)
        if value is None:
            continue
        if existing is None or _differs(kind, value, existing.get(option), all_tokens):
            changes[option] = value
            params.append("{0} {1}".format(cli_param, _cli_value(kind, value)))

    if desired_rights is not None:
        have = set(existing.get("rights", [])) if existing else set()
        if existing is None or have != set(desired_rights):
            changes["rights"] = sorted(desired_rights)
            if existing is None:
                if desired_rights:
                    params.append("permissions " + ",".join(sorted(desired_rights)))
            else:
                params.append("permissions " + rights_argument(desired_rights, supported, have))

    if existing is None:
        command = "set groups add {0}".format(name)
        if params:
            command += " " + " ".join(params)
        return {"action": "add", "commands": [command], "changes": changes, "dropped_rights": dropped}
    if not params:
        return {"action": "none", "commands": [], "changes": {}, "dropped_rights": dropped}
    return {
        "action": "edit",
        "commands": ["set groups edit {0} {1}".format(existing["name"], " ".join(params))],
        "changes": changes,
        "dropped_rights": dropped,
    }


def tombstone_name(name, prefix, current):
    """A free name of at most 30 characters for a revoked group."""
    base = (prefix + name)[:MAX_NAME_LENGTH]
    if base.lower() not in current:
        return base
    for n in range(2, 100):
        suffix = "-{0}".format(n)
        candidate = base[:MAX_NAME_LENGTH - len(suffix)] + suffix
        if candidate.lower() not in current:
            return candidate
    return None


def plan_absent(name, current, method, prefix):
    """Plan removal of one group on one device.

    revoke: remove every right, then rename so the directory group no longer
    matches. delete: remove the group outright.
    """
    existing = current.get(name.lower())
    if existing is None:
        return {"action": "none", "commands": [], "renamed_to": None}
    if method == "delete":
        return {"action": "delete", "commands": ["set groups delete {0}".format(existing["name"])], "renamed_to": None}
    commands = []
    if existing.get("rights"):
        commands.append("set groups edit {0} permissions {1}".format(
            existing["name"], ",".join("-" + r for r in sorted(existing["rights"]))))
    new_name = tombstone_name(name, prefix, current)
    if new_name is None:
        return {"action": "error", "commands": [], "renamed_to": None}
    commands.append("set groups rename {0} newname {1}".format(existing["name"], new_name))
    return {"action": "revoke", "commands": commands, "renamed_to": new_name}


def command_failed(results_text, error_text):
    """Return an error message when a write command did not apply."""
    error_text = (error_text or "").strip()
    if error_text and error_text.lower() != "no error":
        return error_text
    text = clean_output(results_text).strip()
    if SUCCESS_TEXT in text.lower():
        return None
    return text or "no result returned"
