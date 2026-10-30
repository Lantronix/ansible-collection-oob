# oob_coverage_gate

Stops a change before it starts when any device it touches has no ready out-of-band console path. A device is covered when its console port is cabled, in NetBox or Nautobot, to an SLC 9000 port that Percepxion manages and reports as ready (`Managed` or `Identified` by default).

The role runs the console coverage gate (the NetBox script `ConsoleCoverageGate` or the Nautobot job `AOOB console coverage gate`) for the hosts in the play, prints which devices are not covered and why, and fails the play for every host if any are not covered. It runs once per play on the control node and changes nothing, so it also runs in check mode.

## Requirements

- The console coverage gate installed in NetBox (as a custom script) or Nautobot (as a job, enabled).
- An API token that can view the devices and run the script or job.
- Device names in the play that match the source of truth, or set `oob_coverage_gate_devices`.

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `oob_coverage_gate_source` | `netbox` | `netbox` or `nautobot` |
| `oob_coverage_gate_url` | `NETBOX_URL` / `NAUTOBOT_URL` | Base URL of the source of truth |
| `oob_coverage_gate_token` | `NETBOX_TOKEN` / `NAUTOBOT_TOKEN` | API token |
| `oob_coverage_gate_script` | `ConsoleCoverageGate` / `AOOB console coverage gate` | Script or job name, or its ID |
| `oob_coverage_gate_devices` | hosts in the play | Device names to check. An empty list checks every active device in the filters below |
| `oob_coverage_gate_site` | `""` | NetBox site (ID or slug) or Nautobot location (ID) |
| `oob_coverage_gate_roles` | `[]` | Device roles (NetBox ID or slug, Nautobot ID) |
| `oob_coverage_gate_tags` | `[]` | Tags (NetBox ID or slug, Nautobot ID) |
| `oob_coverage_gate_ready_states` | `[Managed, Identified]` | Port states that count as ready |
| `oob_coverage_gate_include_console_servers` | `false` | Also grade the SLCs' own console cables |
| `oob_coverage_gate_require_all_devices` | `true` | Fail when a requested device is not in the report (unknown name, not active, or not visible to the token) |
| `oob_coverage_gate_min_in_scope` | `1` | Fail when fewer devices are in scope |
| `oob_coverage_gate_fail` | `true` | Set to `false` to only report |
| `oob_coverage_gate_validate_certs` | `true` | Verify TLS certificates |
| `oob_coverage_gate_wait_seconds` | `120` | How long to wait for the gate run |

The full report (`aoob.console-coverage/v1`) is left in `oob_coverage_gate_report`, with `oob_coverage_gate_uncovered` and `oob_coverage_gate_missing` alongside it. `oob_coverage_gate_missing` combines the report's `not_found` list with any requested name absent from the report, so it also works with gate versions that predate `not_found`.

## Example Playbook

Run the gate before a change to the same hosts:

```yaml
- hosts: access_switches
  gather_facts: false
  roles:
    - role: lantronix.oob.oob_coverage_gate
  tasks:
    - name: The change itself
      cisco.ios.ios_config:
        src: change.cfg
```

Example output when a device has no ready console path:

```text
Console coverage: fail, 1 of 2 device(s) covered
not covered: dist-sw-02: port_state_not_ready
```

Reason codes: `no_console_port`, `no_console_cable`, `peer_not_visible`, `peer_not_console_server`, `slc_not_synced`, `port_name_unparsed`, `no_slc_host`, `port_state_unknown`, `port_state_not_ready`.
