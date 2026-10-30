from __future__ import absolute_import, division, print_function
__metaclass__ = type

import asyncio
import importlib.util
import io
import json
import os
from urllib.error import HTTPError

import pytest

_PLUGIN = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "..", "..",
    "extensions", "eda", "plugins", "event_source", "percepxion_events.py",
)
_spec = importlib.util.spec_from_file_location("percepxion_events", os.path.abspath(_PLUGIN))
pe = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pe)

TENANT = "11111111-2222-3333-4444-555555555555"


def device(did="dev-1", name="slc-lab-01", status="Connected", model="SLC9032"):
    return {
        "device_id": did,
        "device_name": name,
        "serial_num": "FIXTURE0032",
        "status": status,
        "attributes": {"model": model},
        "tenant": [{"id": TENANT}],
    }


def dp_group(port, attached, status="Managed", hostname="sw1", model="WS-C2960X", serial="S1"):
    items = [
        {"name": "telemetry/port:{0}/status_record/dp_info/status".format(port), "value": status},
        {"name": "telemetry/port:{0}/status_record/dp_info/managed_device".format(port),
         "value": "Yes" if attached else "No"},
    ]
    if attached:
        items += [
            {"name": "x/md_type", "value": "Cisco IOS"},
            {"name": "x/md_version", "value": "15.2(7)E8"},
            {"name": "x/md_model", "value": model},
            {"name": "x/md_sn", "value": serial},
            {"name": "x/md_hostname", "value": hostname},
            {"name": "x/md_ipv4_mgmt", "value": ""},
            {"name": "x/running_config", "value": "secret config"},
        ]
    return {"name": "telemetry/port:{0}/status_record/dp_info".format(port), "items": items}


def view(*groups):
    return {"status_record": list(groups) + [{"name": "telemetry/system/status_record", "items": []}]}


class FakeResponse(object):
    def __init__(self, body, code=200):
        self._body = json.dumps(body).encode("utf-8")
        self._code = code

    def getcode(self):
        return self._code

    def read(self):
        return self._body


class FakeApi(object):
    """Stands in for urlopen. ``routes`` maps a path to a list of responses, consumed in order."""

    def __init__(self, routes):
        self.routes = dict((k, list(v)) for k, v in routes.items())
        self.calls = []

    def __call__(self, req, timeout=None, context=None):
        path = "/" + req.full_url.split("/api/", 1)[1]
        self.calls.append((path, dict(req.header_items()), json.loads(req.data.decode("utf-8"))))
        queue = self.routes[path]
        item = queue.pop(0) if len(queue) > 1 else queue[0]
        if isinstance(item, int):
            raise HTTPError(req.full_url, item, "error", {}, io.BytesIO(b"body must not leak"))
        return FakeResponse(item)


LOGIN = {"token": "tok", "csrf_token": "csrf", "expires_in": 1800}


def poller(api, **kw):
    kw.setdefault("request_interval", 0)
    return pe.PercepxionPoller("api.example.test", "user", "pw", opener=api, sleep=lambda s: None, **kw)


def test_parse_port_states_reads_only_dp_info():
    states = pe.parse_port_states(view(dp_group(14, True), dp_group(3, False, status="Disconnected")))
    assert set(states) == {3, 14}
    assert states[3] == {"state": "Disconnected", "attached": False}
    assert states[14]["make"] == "Cisco" and states[14]["os"] == "IOS"
    assert states[14]["hostname"] == "sw1"
    assert "running_config" not in states[14]


def test_parse_port_states_tolerates_junk():
    assert pe.parse_port_states(None) == {}
    assert pe.parse_port_states({"status_record": ["x", {"name": None}]}) == {}


@pytest.mark.parametrize("prev,cur,expected", [
    (None, {"attached": True}, "attached"),
    ({"attached": True}, {"attached": False}, "detached"),
    ({"attached": True, "hostname": "a"}, {"attached": True, "hostname": "b"}, "changed"),
    ({"attached": True, "hostname": "a"}, {"attached": True, "hostname": "a"}, None),
    ({"attached": False}, {"attached": False}, None),
])
def test_port_change(prev, cur, expected):
    assert pe.port_change(prev, cur) == expected


def test_status_events_baseline_is_silent():
    assert pe.status_events(None, [device()], "2026-10-30T00:00:00Z", None) == []


def test_status_events_emit_initial():
    events = pe.status_events(None, [device()], "2026-10-30T00:00:00Z", None, emit_initial=True)
    assert events[0]["data"] == {"status": "Connected", "previous_status": "", "up": True}


def test_status_events_transition():
    events = pe.status_events({"dev-1": "Connected"}, [device(status="Disconnected")], "2026-10-30T00:00:00Z", None)
    assert len(events) == 1
    ev = events[0]
    assert ev["type"] == "percepxion.device.status_changed"
    assert ev["source"] == "lantronix.oob.percepxion_events"
    assert ev["tenant_id"] == TENANT
    assert ev["device"] == {"id": "dev-1", "name": "slc-lab-01", "serial": "FIXTURE0032", "model": "SLC9032"}
    assert ev["data"] == {"status": "Disconnected", "previous_status": "Connected", "up": False}
    assert ev["id"].startswith("rly-")


def test_status_events_skips_unchanged_and_new_devices():
    devices = [device(), device(did="dev-2", status="Disconnected")]
    assert pe.status_events({"dev-1": "Connected"}, devices, "t", None) == []


def test_event_id_is_stable():
    a = pe.status_events({"dev-1": "Connected"}, [device(status="Disconnected")], "t", None)[0]["id"]
    b = pe.status_events({"dev-1": "Connected"}, [device(status="Disconnected")], "t", None)[0]["id"]
    c = pe.status_events({"dev-1": "Connected"}, [device(status="Disconnected")], "t2", None)[0]["id"]
    assert a == b != c


def test_configured_tenant_wins():
    ev = pe.status_events({"dev-1": "Connected"}, [device(status="Disconnected")], "t", "other-tenant")[0]
    assert ev["tenant_id"] == "other-tenant"


def test_port_events_attached_detached_changed():
    prev = pe.parse_port_states(view(dp_group(1, False), dp_group(2, True), dp_group(3, True, hostname="old")))
    cur = pe.parse_port_states(view(dp_group(1, True), dp_group(2, False), dp_group(3, True, hostname="new")))
    events = pe.port_events(device(), prev, cur, "t", None)
    by_port = dict((e["data"]["port"], e["data"]) for e in events)
    assert by_port[1]["change"] == "attached" and by_port[1]["previous"] is None
    assert by_port[2]["change"] == "detached" and by_port[2]["attached_device"] is None
    assert by_port[3]["change"] == "changed"
    assert by_port[3]["previous"]["hostname"] == "old" and by_port[3]["attached_device"]["hostname"] == "new"
    assert set(by_port[1]["attached_device"]) == {"make", "os", "os_version", "model", "serial", "hostname", "ip"}


def test_port_events_initial():
    cur = pe.parse_port_states(view(dp_group(1, True), dp_group(2, False)))
    assert pe.port_events(device(), None, cur, "t", None) == []
    events = pe.port_events(device(), None, cur, "t", None, emit_initial=True)
    assert [e["data"]["port"] for e in events] == [1]


@pytest.mark.parametrize("dev,port_devices,expected", [
    (device(), (), True),
    (device(model="NTC_501"), (), False),
    (device(status="Disconnected"), (), False),
    (device(model="NTC_501"), {"slc-lab-01"}, True),
    (device(), {"dev-9"}, False),
])
def test_wants_ports(dev, port_devices, expected):
    assert pe.wants_ports(dev, port_devices) is expected


def test_poll_end_to_end():
    api = FakeApi({
        "/v2/user/login": [LOGIN],
        "/v3/device/search": [
            {"search_results": [device()]},
            {"search_results": [device(status="Disconnected")]},
        ],
        "/v1/telemetry/stat/view": [view(dp_group(14, False))],
    })
    p = poller(api, tenant_id=TENANT)
    assert p.poll({"status", "ports"}) == []
    events = p.poll({"status", "ports"})
    assert [e["type"] for e in events] == ["percepxion.device.status_changed"]
    login_path, login_headers, _body = api.calls[0]
    assert login_path == "/v2/user/login" and "X-mystq-token" not in login_headers
    search = api.calls[1]
    assert search[1]["X-mystq-token"] == "tok" and search[1]["X-csrf-token"] == "csrf"
    assert search[2]["tenant_id"] == TENANT
    # The disconnected device's ports are not read on the second poll.
    assert [c[0] for c in api.calls].count("/v1/telemetry/stat/view") == 1


def test_poll_port_change():
    api = FakeApi({
        "/v2/user/login": [LOGIN],
        "/v3/device/search": [{"search_results": [device()]}],
        "/v1/telemetry/stat/view": [view(dp_group(14, False)), view(dp_group(14, True, hostname="edge-01"))],
    })
    p = poller(api)
    assert p.poll({"ports"}) == []
    events = p.poll({"ports"})
    assert len(events) == 1
    assert events[0]["data"]["change"] == "attached"
    assert events[0]["data"]["attached_device"]["hostname"] == "edge-01"


def test_device_seen_after_first_poll_is_baselined_quietly():
    api = FakeApi({
        "/v2/user/login": [LOGIN],
        "/v3/device/search": [{"search_results": []}, {"search_results": [device()]}],
        "/v1/telemetry/stat/view": [view(dp_group(14, True))],
    })
    p = poller(api)
    assert p.poll({"status", "ports"}, emit_initial=True) == []
    assert p.poll({"status", "ports"}) == []
    assert 14 in p.ports["dev-1"]


def test_telemetry_failure_skips_device():
    api = FakeApi({
        "/v2/user/login": [LOGIN],
        "/v3/device/search": [{"search_results": [device()]}],
        "/v1/telemetry/stat/view": [500],
    })
    p = poller(api)
    assert p.poll({"ports"}) == []
    assert p.ports == {}


def test_401_relogs_in_once():
    api = FakeApi({
        "/v2/user/login": [LOGIN],
        "/v3/device/search": [401, {"search_results": []}],
    })
    p = poller(api)
    p.devices()
    assert [c[0] for c in api.calls] == ["/v2/user/login", "/v3/device/search", "/v2/user/login", "/v3/device/search"]


def test_second_401_is_auth_error():
    api = FakeApi({"/v2/user/login": [LOGIN], "/v3/device/search": [401]})
    with pytest.raises(pe.PercepxionAuthError):
        poller(api).devices()


def test_login_rejected_hides_credentials():
    api = FakeApi({"/v2/user/login": [401]})
    with pytest.raises(pe.PercepxionAuthError) as exc:
        poller(api).devices()
    assert "pw" not in str(exc.value) and "body must not leak" not in str(exc.value)
    assert "pw" not in repr(poller(api))


def test_server_error_message_has_no_body():
    api = FakeApi({"/v2/user/login": [LOGIN], "/v3/device/search": [502]})
    with pytest.raises(pe.PercepxionError) as exc:
        poller(api).devices()
    assert str(exc.value) == "POST /v3/device/search returned HTTP 502"


def test_pagination():
    page1 = {"search_results": [device(did="d{0}".format(i)) for i in range(50)], "sort_last": ["d49"]}
    page2 = {"search_results": [device(did="last")], "sort_last": ["last"]}
    api = FakeApi({"/v2/user/login": [LOGIN], "/v3/device/search": [page1, page2]})
    assert len(poller(api).devices()) == 51
    assert api.calls[2][2]["search_after"] == ["d49"]


def test_pacing_sleeps_between_requests():
    slept = []
    api = FakeApi({"/v2/user/login": [LOGIN], "/v3/device/search": [{"search_results": []}]})
    p = pe.PercepxionPoller("api.example.test", "u", "p", request_interval=1.0, opener=api,
                            clock=lambda: 100.0, sleep=slept.append)
    p.devices()
    assert slept == [1.0]


def test_build_poller_env_fallback(monkeypatch):
    monkeypatch.setenv("PERCEPXION_USERNAME", "envuser")
    monkeypatch.setenv("PERCEPXION_PASSWORD", "envpw")
    p = pe.build_poller({"host": "api.example.test"})
    assert p.base == "https://api.example.test/api"


def test_build_poller_requires_host_and_credentials(monkeypatch):
    monkeypatch.delenv("PERCEPXION_USERNAME", raising=False)
    monkeypatch.delenv("PERCEPXION_PASSWORD", raising=False)
    with pytest.raises(ValueError):
        pe.build_poller({})
    with pytest.raises(ValueError):
        pe.build_poller({"host": "api.example.test"})


def test_main_puts_events_on_queue(monkeypatch):
    calls = []

    class StubPoller(object):
        def poll(self, watch, port_devices, emit_initial):
            calls.append(emit_initial)
            return [{"id": "rly-1"}] if len(calls) == 1 else []

    class Stop(Exception):
        pass

    async def fake_sleep(_seconds):
        if len(calls) >= 2:
            raise Stop()

    monkeypatch.setattr(pe, "build_poller", lambda args: StubPoller())
    monkeypatch.setattr(pe.asyncio, "sleep", fake_sleep)
    queue = asyncio.Queue()
    with pytest.raises(Stop):
        asyncio.run(pe.main(queue, {"host": "h", "emit_initial": True}))
    assert queue.get_nowait() == {"id": "rly-1"}
    assert calls == [True, False]


def test_main_survives_transient_error(monkeypatch):
    calls = []

    class StubPoller(object):
        def poll(self, watch, port_devices, emit_initial):
            calls.append(emit_initial)
            if len(calls) == 1:
                raise pe.PercepxionError("POST /v3/device/search returned HTTP 503")
            return []

    class Stop(Exception):
        pass

    async def fake_sleep(_seconds):
        if len(calls) >= 2:
            raise Stop()

    monkeypatch.setattr(pe, "build_poller", lambda args: StubPoller())
    monkeypatch.setattr(pe.asyncio, "sleep", fake_sleep)
    with pytest.raises(Stop):
        asyncio.run(pe.main(asyncio.Queue(), {"host": "h", "emit_initial": True}))
    # emit_initial stays on until a poll succeeds.
    assert calls == [True, True]


def test_main_stops_on_auth_error(monkeypatch):
    class StubPoller(object):
        def poll(self, *args):
            raise pe.PercepxionAuthError("Percepxion login rejected (HTTP 401)")

    monkeypatch.setattr(pe, "build_poller", lambda args: StubPoller())
    with pytest.raises(pe.PercepxionAuthError):
        asyncio.run(pe.main(asyncio.Queue(), {"host": "h"}))
