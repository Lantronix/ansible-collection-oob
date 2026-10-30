# lantronix.oob Ansible Collection

Manage Lantronix Out-of-Band infrastructure from Ansible. The `lantronix.oob` collection provides 21 active modules covering SLC9000 device configuration and Percepxion fleet management, the only Ansible collection that automates the full OOB infrastructure stack, not just the appliance.

## Installation

Install from Red Hat Ansible Automation Hub with the `ansible-galaxy` command-line tool:

```bash
ansible-galaxy collection install lantronix.oob
```

Or add it to a `requirements.yml` file and run `ansible-galaxy collection install -r requirements.yml`:

```yaml
collections:
  - name: lantronix.oob
```

To install a specific version, or upgrade to the latest release:

```bash
ansible-galaxy collection install lantronix.oob:==1.3.0
ansible-galaxy collection install lantronix.oob --upgrade
```

## Requirements

- Python 3.9 or later
- Python `requests` library (declared in `requirements.txt`; execution environments built with `ansible-builder` include it automatically)
- `ansible.netcommon` >= 5.0.0 (installed automatically as a collection dependency)
- `netbox.netbox` >= 3.21.0 (installed automatically as a collection dependency; its Python requirements are needed only for the NetBox integration playbook)

The minimum supported `ansible-core` version is declared in `meta/runtime.yml`.

## Supported Platforms

| Platform | Connection Plugin | API |
|---|---|---|
| SLC9000 (firmware R8+) | `lantronix.oob.slc9` | REST API v2 (OpenAPI 3.1.0) |
| Percepxion 6.12+ | `lantronix.oob.percepxion` | OpenAPI 3.0.1 |

## Modules

### SLC9000 Device Modules

| Module | What it does |
|---|---|
| `lantronix.oob.slc_facts` | Gather hardware/firmware/status facts |
| `lantronix.oob.slc_users` | Manage local user accounts |
| `lantronix.oob.slc_network` | Configure ethernet interfaces |
| `lantronix.oob.slc_system` | Manage hostname, NTP, timezone, reboot |
| `lantronix.oob.slc_device_ports` | Query serial/console port configuration |
| `lantronix.oob.slc_firmware` | Check firmware version, trigger upgrades |
| `lantronix.oob.slc_config` | Backup, compare, batch commands, save config |
| `lantronix.oob.slc_managed_devices` | Query devices connected via serial ports |

### Percepxion Fleet Modules

| Module | What it does |
|---|---|
| `lantronix.oob.percepxion_facts` | Gather fleet summary and platform facts |
| `lantronix.oob.percepxion_devices` | Query and update device inventory |
| `lantronix.oob.percepxion_projects` | Manage device project assignments |
| `lantronix.oob.percepxion_smart_groups` | Create and manage device smart groups |
| `lantronix.oob.percepxion_firmware` | Fleet firmware compliance report and upgrade |
| `lantronix.oob.percepxion_config` | Config backup, restore, push at fleet scale |
| `lantronix.oob.percepxion_jobs` | Job group lifecycle, create, schedule, monitor |
| `lantronix.oob.percepxion_audit_logs` | Security audit log query and device access log export |
| `lantronix.oob.percepxion_import_devices` | Bulk device import and project assignment |
| `lantronix.oob.percepxion_telemetry` | Device telemetry stats and historical data |
| `lantronix.oob.percepxion_event_rules` | Create, update, delete event rules and email/SMS notification actions |
| `lantronix.oob.percepxion_device_tags` | Create device tags and assign or unassign them to devices |
| `lantronix.oob.percepxion_users` | Create, delete, suspend, and resume user accounts; bulk suspend/resume by username or email, allowlist lockdown mode |
| `lantronix.oob.percepxion_aoob_session` | *(Deprecated, removed in 2.0.0)* Connect/disconnect endpoints are device-token authenticated, not reachable with user credentials. Use the Percepxion web interface. |

## Example Roles

| Role | What it does |
|---|---|
| `lantronix.oob.oob_fleet_inventory` | Queries Percepxion and generates a dynamic Ansible inventory |
| `lantronix.oob.oob_firmware_audit` | Checks fleet firmware compliance, optionally triggers upgrades |
| `lantronix.oob.oob_user_management` | Bulk user management across all SLC devices in a smart group |
| `lantronix.oob.oob_baseline_config` | Enforces baseline hostname, NTP, and syslog config across SLC fleet |
| `lantronix.oob.oob_coverage_gate` | Stops a change when the devices it touches have no ready console path through an SLC (NetBox or Nautobot console coverage gate) |

## NetBox Integration

`playbooks/combo/netbox_sync.yml` keeps NetBox current with your out-of-band estate:

- Creates a `lantronix_itmgos` platform (the slug matches the Netmiko device type for SLC and EMG), a `percepxion_device_id` custom field, and "Open console (SSH)" and "SLC web UI" links on console server ports.
- Publishes a config context with the `lantronix.oob` connection settings for SLC 9000 device types, so the `netbox.netbox.nb_inventory` plugin can serve NetBox as your inventory for this collection.
- Records each SLC 9000 in NetBox with its device type and serial number, and writes each serial port's configured name and attached device to the matching console server port (`Port-01`, `Port-02`, and so on).
- Records every SLC and EMG managed by Percepxion, with its serial number and Percepxion device ID. Existing NetBox devices keep their device type.
- Updates an existing NetBox device only when it is the same Lantronix unit (matching or empty serial number, `lantronix_itmgos` or no platform, in `netbox_site`). Name collisions with other devices are reported and left unchanged.

The playbook uses the `netbox.netbox` collection (installed automatically as a collection dependency) and its Python requirements on the control node, plus the Lantronix device types from the NetBox community device type library.

```bash
export NETBOX_URL=https://netbox.example.com NETBOX_TOKEN=<api token>
ansible-playbook -i inventory.yml playbooks/combo/netbox_sync.yml \
  -e "netbox_site=dc1 netbox_device_role=console-server netbox_mgmt_prefix_length=24"
```

Use `--tags setup`, `--tags slc` or `--tags percepxion` to run one part.

## Event-Driven Ansible

The `lantronix.oob.percepxion_events` event source polls Percepxion and emits an event when:

- a managed device's connection status changes (`percepxion.device.status_changed`, with `data.status`, `data.previous_status` and `data.up`)
- the device attached to an SLC console port appears, changes, or goes away (`percepxion.port.attached_changed`, with `data.port`, `data.change`, `data.state`, `data.attached_device` and `data.previous`)

Each event carries the device's Percepxion ID, name, serial number and model in `event.device`, and a stable `event.id`. The first poll records a baseline and emits nothing unless `emit_initial: true`. Port changes are read from each connected SLC's telemetry, one request per SLC per poll; `port_devices` limits which devices are read.

The collection ships the `lantronix.oob.percepxion_console_events` rulebook, which runs `lantronix.oob.eda_device_offline` when a device goes offline and `lantronix.oob.eda_port_attached` when a console port changes. Both playbooks are read-only reports to extend with your own actions.

```bash
export PERCEPXION_USERNAME=<user> PERCEPXION_PASSWORD=<password>
ansible-rulebook -r lantronix.oob.percepxion_console_events -i inventory.yml \
  --vars rulebook_vars.yml   # percepxion_host: api.percepxion.ai
```

Or use the source in your own rulebook:

```yaml
sources:
  - lantronix.oob.percepxion_events:
      host: api.percepxion.ai
      interval: 60
      watch: [status, ports]
rules:
  - name: New device on a console port
    condition: event.type == "percepxion.port.attached_changed" and event.data.change == "attached"
    action:
      debug:
        msg: "{{ event.device.name }} port {{ event.data.port }}: {{ event.data.attached_device.hostname }}"
```

The event source needs no Python packages beyond the standard library.

## Quick Start

### SLC9000

```yaml
# inventory.yml
slc_devices:
  hosts:
    slc9k-datacenter:
      ansible_host: 192.0.2.100
  vars:
    ansible_network_os: lantronix.oob.slc9
    ansible_connection: ansible.netcommon.httpapi
    ansible_httpapi_use_ssl: true
    ansible_httpapi_validate_certs: true
    ansible_user: sysadmin
    ansible_password: "{{ vault_slc_password }}"
```

```yaml
# gather_facts.yml
- hosts: slc_devices
  gather_facts: false
  tasks:
    - name: Gather SLC facts
      lantronix.oob.slc_facts:
      register: result

    - name: Show firmware and model
      ansible.builtin.debug:
        msg: "{{ inventory_hostname }}, {{ result.slc_facts.model }} running {{ result.slc_facts.firmware_version }}"
```

### Percepxion

```yaml
# inventory.yml
percepxion:
  hosts:
    percepxion_platform:
      ansible_host: api.consoleflow.com
  vars:
    ansible_network_os: lantronix.oob.percepxion
    ansible_connection: ansible.netcommon.httpapi
    ansible_httpapi_use_ssl: true
    ansible_user: "{{ vault_percepxion_user }}"
    ansible_password: "{{ vault_percepxion_password }}"
    percepxion_project_tag: "prod-datacenter-east"   # optional, scopes all ops to project
    percepxion_tenant_id: "34f5c98e-..."             # optional, Project Admin only
```

```yaml
# firmware_audit.yml
- hosts: percepxion_platform
  gather_facts: false
  tasks:
    - name: Run firmware compliance report
      lantronix.oob.percepxion_firmware:
        state: report
      register: audit

    - name: Show non-compliant devices
      ansible.builtin.debug:
        msg: "Non-compliant: {{ audit.firmware_report.non_compliant | map(attribute='device_name') | list }}"
```

## Connection Plugins

This collection includes two httpapi connection plugins:

- **`lantronix.oob.slc9`**, authenticates to SLC9000 REST API v2 via session token
- **`lantronix.oob.percepxion`**, authenticates to Percepxion API with Bearer token and CSRF token handling

Both plugins handle login, token management, and error translation automatically. You do not call them directly; set `ansible_network_os` in your inventory.

## Percepxion Project and Tenant Scoping

The Percepxion API supports multi-project and multi-tenant deployments. Set these as inventory connection variables, all Percepxion modules inherit them automatically:

```yaml
percepxion_project_tag: "prod-east"       # scope all ops to this project
percepxion_tenant_id: "uuid-here"         # required only for Project Admins
```

To operate across multiple projects, loop over inventory groups rather than module arguments.

## Contributing

Bug reports and pull requests welcome. Please open an issue before submitting a PR for significant changes.

See [CONTRIBUTING.md](https://github.com/Lantronix/ansible-collection-oob/blob/main/CONTRIBUTING.md) for development setup, coding standards, and commit conventions.

## Changelog

See [CHANGELOG.rst](https://github.com/Lantronix/ansible-collection-oob/blob/main/CHANGELOG.rst) for release history.

## Support

This collection is maintained by the Lantronix OOB product team.

**Red Hat Automation Hub users:** Open a support request via the [collection page on Automation Hub](https://console.redhat.com/ansible/automation-hub/repo/published/lantronix/oob) using the "Create issue" link. This ensures your request is routed through the appropriate Red Hat support channels.

**Community support:** Open an issue on [GitHub](https://github.com/Lantronix/ansible-collection-oob/issues). Pull requests are welcome, please open an issue before submitting a PR for significant changes.

**Product support:** Visit [https://www.lantronix.com/support/](https://www.lantronix.com/support/).

## License

Apache 2.0. See [LICENSE](https://github.com/Lantronix/ansible-collection-oob/blob/main/LICENSE) for details.
