from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
name: percepxion_events
short_description: Poll Percepxion for device status and console port changes
version_added: "1.4.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - An Event-Driven Ansible event source that polls the Percepxion REST API and
    emits an event when a managed device's connection status changes or when the
    device attached to an SLC console port changes.
  - Events use the Percepxion webhook envelope (C(spec_version) 1), so a rulebook
    that matches on C(event.type) and C(event.data) keeps working if the events
    later arrive by webhook instead.
  - The first poll records a baseline and emits nothing unless I(emit_initial) is
    true. State is held in memory, so a restart takes a new baseline.
  - Port changes come from each device's telemetry view, one request per
    connected device per poll. Use I(port_devices) to limit which devices are read.
  - Percepxion's own offline detection lags several minutes behind the device, and
    status events inherit that delay.
options:
  host:
    description:
      - Percepxion API host name, for example C(api.percepxion.ai). Requests go to
        C(https://<host>/api).
    type: str
    required: true
  username:
    description:
      - Percepxion user name. Falls back to the C(PERCEPXION_USERNAME) environment variable.
    type: str
  password:
    description:
      - Percepxion password. Falls back to the C(PERCEPXION_PASSWORD) environment variable.
    type: str
  tenant_id:
    description:
      - Tenant to act on. Needed only when the user is not scoped to a single tenant.
    type: str
  validate_certs:
    description:
      - Verify the server's TLS certificate.
    type: bool
    default: true
  interval:
    description:
      - Seconds between polls. Values below 30 are raised to 30.
    type: int
    default: 60
  request_interval:
    description:
      - Minimum seconds between two API requests within a poll.
    type: float
    default: 1.0
  search_string:
    description:
      - Device search expression passed to Percepxion; C(*) matches every device.
    type: str
    default: "*"
  watch:
    description:
      - Which changes to emit.
      - C(status) emits C(percepxion.device.status_changed).
      - C(ports) emits C(percepxion.port.attached_changed).
    type: list
    elements: str
    choices: [status, ports]
    default: [status, ports]
  port_devices:
    description:
      - Device names or IDs whose console ports are watched. Empty watches every
        connected device whose model starts with C(SLC).
    type: list
    elements: str
    default: []
  emit_initial:
    description:
      - On the first poll, emit a status event for every device (with an empty
        C(previous_status)) and an C(attached) event for every port with a device
        attached, instead of only recording a baseline.
    type: bool
    default: false
notes:
  - Requires network access from the ansible-rulebook host to the Percepxion API.
  - Each event carries a stable C(id). The same change seen twice, for example
    across a restart, can produce a second event; deduplicate on C(id) or design
    the triggered playbook to be idempotent.
"""

EXAMPLES = r"""
- name: React to SLC console changes
  hosts: localhost
  sources:
    - lantronix.oob.percepxion_events:
        host: api.percepxion.ai
        interval: 60
        watch: [status, ports]
  rules:
    - name: SLC went offline
      condition: >-
        event.type == "percepxion.device.status_changed" and event.data.up == false
      action:
        run_playbook:
          name: lantronix.oob.eda_device_offline

    - name: New device on a console port
      condition: >-
        event.type == "percepxion.port.attached_changed" and event.data.change == "attached"
      action:
        debug:
          msg: "{{ event.device.name }} port {{ event.data.port }}: {{ event.data.attached_device.hostname }}"
"""

import asyncio
import hashlib
import json
import os
import re
import ssl
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SPEC_VERSION = "1"
SOURCE = "lantronix.oob.percepxion_events"
STATUS_EVENT = "percepxion.device.status_changed"
PORT_EVENT = "percepxion.port.attached_changed"
USER_AGENT = "lantronix.oob-percepxion_events/1"
TIMEOUT = 30
MIN_INTERVAL = 30
SESSION_TTL = 1800
ATTACHED_FIELDS = ("make", "os", "os_version", "model", "serial", "hostname", "ip")
_DP_INFO = re.compile(r"^telemetry/port:(\d+)/status_record/dp_info$")
_DP_KEEP = frozenset(
    ("status", "managed_device", "md_type", "md_version", "md_model", "md_sn", "md_hostname", "md_ipv4_mgmt")
)


class PercepxionError(Exception):
    """Messages carry method, path and status only, never bodies or credentials."""


class PercepxionAuthError(PercepxionError):
    pass


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def event_id(*parts):
    """Stable id for a synthesized event: same transition seen at the same poll, same id."""
    digest = hashlib.sha256("\x1f".join(str(p) for p in parts).encode("utf-8")).hexdigest()
    return "rly-{0}".format(digest[:16])


def device_model(dev):
    attrs = dev.get("attributes")
    return str((attrs.get("model") if isinstance(attrs, dict) else None) or dev.get("model") or "")


def device_tenant(dev, tenant_id=None):
    """The configured tenant, else the first org in the device record's tenant list."""
    if tenant_id:
        return str(tenant_id)
    for org in dev.get("tenant") or []:
        if isinstance(org, dict) and org.get("id") not in (None, ""):
            return str(org["id"])
    return ""


def device_block(dev):
    return {
        "id": str(dev.get("device_id") or ""),
        "name": str(dev.get("device_name") or ""),
        "serial": str(dev.get("serial_num") or ""),
        "model": device_model(dev),
    }


def envelope(event_type, dev, data, occurred_at, tenant_id, eid):
    return {
        "spec_version": SPEC_VERSION,
        "id": eid,
        "type": event_type,
        "source": SOURCE,
        "occurred_at": occurred_at,
        "tenant_id": device_tenant(dev, tenant_id),
        "device": device_block(dev),
        "data": data,
    }


def parse_port_states(raw):
    """Map port number to attached-device state from a telemetry view response.

    Reads only the dp_info fields in _DP_KEEP; configurations and other telemetry in the
    response are ignored.
    """
    states = {}
    groups = raw.get("status_record") if isinstance(raw, dict) else None
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        match = _DP_INFO.match(str(group.get("name") or ""))
        if not match:
            continue
        values = {}
        for item in group.get("items") or []:
            if not isinstance(item, dict):
                continue
            key = str(item.get("name") or "").rsplit("/", 1)[-1]
            if key in _DP_KEEP:
                values[key] = str(item.get("value") or "").strip()
        attached = values.get("managed_device", "").lower() == "yes"
        state = {"state": values.get("status", ""), "attached": attached}
        if attached:
            make, _sep, os_name = values.get("md_type", "").strip().partition(" ")
            state.update(
                make=make,
                os=os_name.strip(),
                os_version=values.get("md_version", ""),
                model=values.get("md_model", ""),
                serial=values.get("md_sn", ""),
                hostname=values.get("md_hostname", ""),
                ip=values.get("md_ipv4_mgmt", ""),
            )
        states[int(match.group(1))] = state
    return states


def attached_block(state):
    if not state or not state.get("attached"):
        return None
    return dict((k, str(state.get(k) or "")) for k in ATTACHED_FIELDS)


def port_change(prev, cur):
    """attached, detached, changed or None between two port states."""
    was = bool(prev and prev.get("attached"))
    now = bool(cur and cur.get("attached"))
    if not was and now:
        return "attached"
    if was and not now:
        return "detached"
    if was and now and any(prev.get(k) != cur.get(k) for k in ("hostname", "model", "serial")):
        return "changed"
    return None


def status_events(previous, devices, occurred_at, tenant_id, emit_initial=False):
    """Compare device statuses to the last poll. ``previous`` is None on the first poll."""
    events = []
    for dev in devices:
        did = str(dev.get("device_id") or "")
        if not did:
            continue
        status = str(dev.get("status") or "")
        if previous is None:
            if not emit_initial:
                continue
            before = ""
        else:
            if did not in previous or previous[did] == status:
                continue
            before = previous[did]
        data = {"status": status, "previous_status": before, "up": status == "Connected"}
        eid = event_id(STATUS_EVENT, did, before, status, occurred_at)
        events.append(envelope(STATUS_EVENT, dev, data, occurred_at, tenant_id, eid))
    return events


def port_events(dev, previous, current, occurred_at, tenant_id, emit_initial=False):
    """Compare one device's port states to the last poll. ``previous`` is None the first time."""
    events = []
    did = str(dev.get("device_id") or "")
    for port in sorted(current):
        cur = current[port]
        if previous is None:
            if not (emit_initial and cur.get("attached")):
                continue
            prev = None
        else:
            if port not in previous:
                continue
            prev = previous[port]
        change = port_change(prev, cur)
        if change is None:
            continue
        data = {
            "port": port,
            "change": change,
            "state": str(cur.get("state") or ""),
            "attached_device": attached_block(cur),
            "previous": attached_block(prev),
        }
        eid = event_id(
            PORT_EVENT, did, port, change, json.dumps(data["previous"], sort_keys=True),
            json.dumps(data["attached_device"], sort_keys=True), occurred_at,
        )
        events.append(envelope(PORT_EVENT, dev, data, occurred_at, tenant_id, eid))
    return events


def wants_ports(dev, port_devices):
    if str(dev.get("status") or "") != "Connected":
        return False
    if port_devices:
        return str(dev.get("device_id") or "") in port_devices or str(dev.get("device_name") or "") in port_devices
    return device_model(dev).upper().startswith("SLC")


class PercepxionPoller(object):
    """Read-only Percepxion client and change tracker for one event source."""

    def __init__(self, host, username, password, tenant_id=None, validate_certs=True,
                 request_interval=1.0, search_string="*", opener=urlopen, clock=time.monotonic,
                 sleep=time.sleep):
        self.base = "https://{0}/api".format(host.strip().rstrip("/"))
        self._login_body = {"username": username, "password": password}
        self.tenant_id = tenant_id
        self.request_interval = request_interval
        self.search_string = search_string
        self._opener = opener
        self._clock = clock
        self._sleep = sleep
        self._ssl = ssl.create_default_context()
        if not validate_certs:
            self._ssl.check_hostname = False
            self._ssl.verify_mode = ssl.CERT_NONE
        self._headers = {}
        self._expires = 0.0
        self._last_call = None
        self.statuses = None
        self.ports = {}

    def __repr__(self):
        return "PercepxionPoller(base={0!r})".format(self.base)

    def _pace(self):
        if self._last_call is not None:
            wait = self.request_interval - (self._clock() - self._last_call)
            if wait > 0:
                self._sleep(wait)
        self._last_call = self._clock()

    def _send(self, path, body, headers):
        self._pace()
        hdrs = {"Accept": "application/json", "Content-Type": "application/json", "User-Agent": USER_AGENT}
        hdrs.update(headers)
        req = Request(self.base + path, data=json.dumps(body).encode("utf-8"), headers=hdrs, method="POST")
        try:
            resp = self._opener(req, timeout=TIMEOUT, context=self._ssl)
            return resp.getcode(), resp.read()
        except HTTPError as exc:
            return exc.code, b""
        except (URLError, OSError) as exc:
            raise PercepxionError("POST {0} failed: {1}".format(path, type(exc).__name__))

    def login(self):
        status, raw = self._send("/v2/user/login", self._login_body, {})
        if status in (400, 401, 403):
            raise PercepxionAuthError("Percepxion login rejected (HTTP {0})".format(status))
        if not 200 <= status < 300:
            raise PercepxionError("POST /v2/user/login returned HTTP {0}".format(status))
        try:
            data = json.loads(raw.decode("utf-8"))
        except ValueError:
            raise PercepxionError("POST /v2/user/login returned non-JSON")
        if not data.get("token"):
            raise PercepxionAuthError("Percepxion login response held no session token")
        ttl = min(int(data.get("expires_in") or SESSION_TTL), SESSION_TTL)
        self._headers = {"x-mystq-token": str(data["token"]), "x-csrf-token": str(data.get("csrf_token") or "")}
        self._expires = self._clock() + ttl - 60

    def call(self, path, body):
        if not self._headers or self._clock() > self._expires:
            self.login()
        status, raw = self._send(path, body, self._headers)
        if status == 401:
            self.login()
            status, raw = self._send(path, body, self._headers)
        if status in (401, 403):
            raise PercepxionAuthError("POST {0} not authorized (HTTP {1})".format(path, status))
        if not 200 <= status < 300:
            raise PercepxionError("POST {0} returned HTTP {1}".format(path, status))
        try:
            return json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            raise PercepxionError("POST {0} returned non-JSON".format(path))

    def _with_tenant(self, body):
        if self.tenant_id:
            body["tenant_id"] = self.tenant_id
        return body

    def devices(self, limit=50, max_pages=200):
        out = []
        after = None
        for _page in range(max_pages):
            body = {"search_string": self.search_string, "limit": limit, "sort": "device_name", "order": "asc"}
            if after is not None:
                body.update(search_after=after, pagination="next")
            data = self.call("/v3/device/search", self._with_tenant(body))
            items = [i for i in (data.get("search_results") or []) if isinstance(i, dict)]
            out.extend(items)
            nxt = data.get("sort_last")
            if len(items) < limit or nxt in (None, "") or nxt == after:
                break
            after = nxt
        return out

    def telemetry(self, device_id):
        return self.call("/v1/telemetry/stat/view", self._with_tenant({"device_id": device_id, "selected": True}))

    def poll(self, watch, port_devices=(), emit_initial=False):
        """One poll: read Percepxion, update the baseline, return the new events."""
        occurred_at = utc_now()
        devices = self.devices()
        events = []
        if "status" in watch:
            events.extend(status_events(self.statuses, devices, occurred_at, self.tenant_id, emit_initial))
        first = self.statuses is None
        self.statuses = dict((str(d.get("device_id")), str(d.get("status") or "")) for d in devices
                             if d.get("device_id"))
        if "ports" in watch:
            for dev in devices:
                if not wants_ports(dev, port_devices):
                    continue
                did = str(dev["device_id"])
                try:
                    current = parse_port_states(self.telemetry(did))
                except PercepxionAuthError:
                    raise
                except PercepxionError:
                    continue
                if not current:
                    continue
                # A device first seen after the first poll is baselined quietly.
                events.extend(port_events(dev, self.ports.get(did), current, occurred_at, self.tenant_id,
                                          emit_initial and first))
                self.ports[did] = current
        return events


def build_poller(args):
    host = args.get("host")
    if not host:
        raise ValueError("percepxion_events: 'host' is required")
    username = args.get("username") or os.environ.get("PERCEPXION_USERNAME")
    password = args.get("password") or os.environ.get("PERCEPXION_PASSWORD")
    if not username or not password:
        raise ValueError("percepxion_events: set username and password, or PERCEPXION_USERNAME and PERCEPXION_PASSWORD")
    return PercepxionPoller(
        host,
        username,
        password,
        tenant_id=args.get("tenant_id"),
        validate_certs=bool(args.get("validate_certs", True)),
        request_interval=float(args.get("request_interval", 1.0)),
        search_string=str(args.get("search_string") or "*"),
    )


async def main(queue, args):
    poller = build_poller(args)
    interval = max(int(args.get("interval", 60)), MIN_INTERVAL)
    watch = set(args.get("watch") or ("status", "ports"))
    port_devices = set(str(d) for d in (args.get("port_devices") or []))
    emit_initial = bool(args.get("emit_initial", False))
    while True:
        started = time.monotonic()
        try:
            events = await asyncio.to_thread(poller.poll, watch, port_devices, emit_initial)
        except PercepxionAuthError:
            raise
        except PercepxionError as exc:
            # Transient API trouble: keep the baseline and try again next interval.
            print("percepxion_events: poll failed: {0}".format(exc))
            events = []
        else:
            emit_initial = False
        for event in events:
            await queue.put(event)
        await asyncio.sleep(max(interval - (time.monotonic() - started), 1))


if __name__ == "__main__":
    # Manual run: PERCEPXION_HOST, PERCEPXION_USERNAME, PERCEPXION_PASSWORD in the environment.

    class _PrintQueue(object):
        async def put(self, event):
            print(json.dumps(event))

    asyncio.run(main(_PrintQueue(), {"host": os.environ.get("PERCEPXION_HOST"), "interval": MIN_INTERVAL}))
