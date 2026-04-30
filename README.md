# lantronix.oob Ansible Collection

Manage Lantronix Out-of-Band infrastructure from Ansible. The `lantronix.oob` collection provides 20 modules covering SLC 9000 device configuration and Percepxion fleet management — the only Ansible collection that automates the full OOB infrastructure stack, not just the appliance.

## Installation

```bash
ansible-galaxy collection install lantronix.oob
```

Requires the `requests` library:

```bash
pip install requests
```

## Requirements

- ansible-core >= 2.14
- ansible.netcommon >= 5.0.0
- Python 3.9+
- Python `requests` library

## Supported Platforms

| Platform | Connection Plugin | API |
|---|---|---|
| SLC 9000 (firmware R8+) | `lantronix.oob.slc9` | REST API v2 (OpenAPI 3.1.0) |
| Percepxion 6.12+ | `lantronix.oob.percepxion` | OpenAPI 3.0.1 |

## Modules

### SLC 9000 Device Modules

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
| `lantronix.oob.percepxion_users` | Manage Percepxion users and roles |
| `lantronix.oob.percepxion_smart_groups` | Create and manage device smart groups |
| `lantronix.oob.percepxion_firmware` | Fleet firmware compliance report and upgrade |
| `lantronix.oob.percepxion_config` | Config backup, restore, push at fleet scale |
| `lantronix.oob.percepxion_jobs` | Job group lifecycle — create, schedule, monitor |
| `lantronix.oob.percepxion_audit_logs` | Security audit log query and device access log export |
| `lantronix.oob.percepxion_aoob_session` | Initiate and terminate OOB sessions |
| `lantronix.oob.percepxion_import_devices` | Bulk device import and project assignment |
| `lantronix.oob.percepxion_telemetry` | Device telemetry stats and historical data |

## Example Roles

| Role | What it does |
|---|---|
| `lantronix.oob.oob_fleet_inventory` | Queries Percepxion and generates a dynamic Ansible inventory |
| `lantronix.oob.oob_firmware_audit` | Checks fleet firmware compliance, optionally triggers upgrades |
| `lantronix.oob.oob_user_management` | Bulk user management across all SLC devices in a smart group |
| `lantronix.oob.oob_baseline_config` | Enforces baseline hostname, NTP, and syslog config across SLC fleet |

## Quick Start

### SLC 9000

```yaml
# inventory.yml
slc_devices:
  hosts:
    slc9k-datacenter:
      ansible_host: 192.168.1.100
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
        msg: "{{ inventory_hostname }} — {{ result.slc_facts.model }} running {{ result.slc_facts.firmware_version }}"
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
    percepxion_project_tag: "prod-datacenter-east"   # optional — scopes all ops to project
    percepxion_tenant_id: "34f5c98e-..."             # optional — Project Admin only
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

- **`lantronix.oob.slc9`** — authenticates to SLC 9000 REST API v2 via session token
- **`lantronix.oob.percepxion`** — authenticates to Percepxion API with Bearer token and CSRF token handling

Both plugins handle login, token management, and error translation automatically. You do not call them directly; set `ansible_network_os` in your inventory.

## Percepxion Project and Tenant Scoping

The Percepxion API supports multi-project and multi-tenant deployments. Set these as inventory connection variables — all Percepxion modules inherit them automatically:

```yaml
percepxion_project_tag: "prod-east"       # scope all ops to this project
percepxion_tenant_id: "uuid-here"         # required only for Project Admins
```

To operate across multiple projects, loop over inventory groups rather than module arguments.

## Competitive Comparison

| Capability | Opengear `opengear.om` | Lantronix `lantronix.oob` |
|---|---|---|
| Module count | 12 | 20 |
| Fleet platform modules | 0 | 12 (Percepxion) |
| Config management | 0 | `slc_config` (7 API endpoints) |
| AOOB session management | None | `percepxion_aoob_session` |
| Firmware compliance + push | None | `percepxion_firmware` |
| Fleet audit log export | None | `percepxion_audit_logs` |
| Multi-project / multi-tenant | None | Built in via connection vars |
| Telemetry query | None | `percepxion_telemetry` |
| Example roles | None | 4 |
| Check mode / idempotency | Yes | Yes |
| Red Hat certification | Yes | Targeting Q4 2026 |

## Status

This collection is in active development. Red Hat Technology Partner application submitted April 2026.

| Component | Status |
|---|---|
| All 20 modules | Complete |
| Unit tests (22 test files) | Complete — CI passing |
| Both httpapi plugins | Complete |
| 4 example roles | Complete |
| Integration tests | In progress |
| CHANGELOG.rst | Pending |
| Red Hat certification | Application submitted — targeting Q4 2026 |
| Galaxy community release | Ready — pending final repo on github.com/Lantronix |

## Contributing

Bug reports and pull requests welcome. Please open an issue before submitting a PR for significant changes.

For development setup, run tests against a local ansible-test environment:

```bash
mkdir -p ansible_collections/lantronix
git clone https://github.com/lantronix/ansible-collection-oob ansible_collections/lantronix/oob
cd ansible_collections/lantronix/oob

# Sanity tests
ansible-test sanity --python 3.11

# Unit tests
ansible-test units --python 3.11
```

## License

Apache 2.0. See [LICENSE](LICENSE) for details.
