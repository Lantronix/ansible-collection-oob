# lantronix.oob Collection, Functional Validation Design

**Date:** 2026-05-23
**Version target:** 1.0.16
**Status:** Approved, ready for implementation planning

---

## Problem Statement

The `lantronix.oob` collection passes `ansible-test sanity`, `ansible-test units`, and pylint with zero errors. But functional bugs exist that none of those tools catch. The firmware bug found in v1.0.15 is the canonical example: `/firmware/update_status` returns a plain-text log (not JSON) while an update is in progress. The integration test for `slc_firmware` ran against an idle device, passed, and shipped. The bug only surfaced against a real device in a transitional state.

Root causes:
1. Integration targets are shallow, 2-8 assertion blocks each, all testing the nominal idle state
2. Write modules are not exercised, no create/modify/delete cycles, no idempotency verification
3. Only one SLC device targeted in `integration_config.yml`; DVT3 unused
4. Non-nominal API response formats are not tested or documented
5. `integration_config.yml` has plaintext credentials, a repeat of the April 2026 git hygiene incident

This spec defines the validation system that closes all five gaps before v1.0.16 ships to Ansible Automation Hub and GitHub.

---

## Scope

- All 20 modules: 8 SLC (`slc_config`, `slc_device_ports`, `slc_facts`, `slc_firmware`, `slc_managed_devices`, `slc_network`, `slc_system`, `slc_users`) and 12 Percepxion (`percepxion_aoob_session`, `percepxion_audit_logs`, `percepxion_config`, `percepxion_devices`, `percepxion_facts`, `percepxion_firmware`, `percepxion_import_devices`, `percepxion_jobs`, `percepxion_projects`, `percepxion_smart_groups`, `percepxion_telemetry`, `percepxion_users`)
- Two physical SLC9000 lab devices
- Percepxion Cisco Live project (DVT3)
- Cisco Catalyst 3560G managed device on DVT3 serial port 1
- GitHub Actions CI pipeline with self-hosted runner

Out of scope: SLC 8000, Control Center, LM-Series, any cloud simulation or mock server.

---

## Device Topology

### DVT, Read-Only Lane

| Variable | Source |
|---|---|
| Host | `SLC9_IP` |
| Username | `SLC9_USER` |
| Password | `SLC9_PASSWORD` |
| Hostname | `SLC9_HOSTNAME` |

Purpose: read-only integration tests (Tier 1). No state changes on this device. If a test fails here, a read path regressed. Percepxion context uses the primary project (`PX_PROJECT_USER`, `PX_PROJECT_PASSWORD`, `PX_API_BASE`).

### DVT3, Write Lane

| Variable | Source |
|---|---|
| Host | `SLC9K_DVT3_IP` |
| Username | `SLC9K_DVT3_USER` |
| Password | `SLC9K_DVT3_PASSWORD` |
| Hostname | `SLC9K_DVT3_HOSTNAME` |
| Percepxion host | `PX_API_BASE_DVT3` |
| Percepxion user | `ANSIBLE_USER` |
| Percepxion password | `ANSIBLE_PASSWORD` |
| Percepxion tenant | `ANSIBLE_TENANT` |
| Percepxion portal | `ANSIBLE_PORTAL` |

Purpose: write cycles, idempotency tests, check_mode verification, managed device tests. Device is mostly default configuration (sysadmin password only). Registered in Percepxion Cisco Live project as `SLC9K_DVT3_PX_DEVICE_NAME`.

### Cisco Catalyst 3560G, Managed Device

| Variable | Source |
|---|---|
| Host | `CISCO_C3560G_IP` |
| Username | `CISCO_C3560G_USERNAME` |
| Password | `CISCO_C3560G_PASSWORD` |
| Console command | `CISCO_C3560G_CONSOLE_COMMAND` |
| DVT3 serial port | `1` (hardcoded) |

Connected to DVT3 serial device port 1, powered on. Used by `slc_managed_devices`, `slc_device_ports`, and `percepxion_aoob_session` managed device test tier. If port 1 is unreachable at suite start, these tests skip cleanly.

---

## Credentials and Vault

### Problem with current state

`tests/integration/integration_config.yml` contains plaintext credentials committed to the repo. This is the same class of issue as the April 2026 incident requiring `git filter-repo` history rewrite.

### Solution

Replace `integration_config.yml` with a vault-encrypted file. The plaintext version becomes `integration_config.yml.example` with placeholder values. Both files are committed; only `.example` is readable.

**`tests/integration/integration_config.vault.yml`** (vault-encrypted, committed):
```yaml
# DVT, read-only lane
slc_dvt_host: "{{ lookup('env', 'SLC9_IP') }}"
slc_dvt_username: "{{ lookup('env', 'SLC9_USER') }}"
slc_dvt_password: "{{ lookup('env', 'SLC9_PASSWORD') }}"

# DVT3, write lane
slc_dvt3_host: "{{ lookup('env', 'SLC9K_DVT3_IP') }}"
slc_dvt3_username: "{{ lookup('env', 'SLC9K_DVT3_USER') }}"
slc_dvt3_password: "{{ lookup('env', 'SLC9K_DVT3_PASSWORD') }}"

# Percepxion, primary project (DVT read-only lane)
percepxion_dvt_host: "{{ lookup('env', 'PX_API_BASE') }}"
percepxion_dvt_username: "{{ lookup('env', 'PX_PROJECT_USER') }}"
percepxion_dvt_password: "{{ lookup('env', 'PX_PROJECT_PASSWORD') }}"

# Percepxion, Cisco Live project (DVT3 write lane)
percepxion_host: "{{ lookup('env', 'PX_API_BASE_DVT3') }}"
percepxion_username: "{{ lookup('env', 'ANSIBLE_USER') }}"
percepxion_password: "{{ lookup('env', 'ANSIBLE_PASSWORD') }}"
percepxion_tenant_id: "{{ lookup('env', 'ANSIBLE_TENANT') }}"
percepxion_portal: "{{ lookup('env', 'ANSIBLE_PORTAL') }}"

# Cisco C3560G, managed device on DVT3 port 1
cisco_host: "{{ lookup('env', 'CISCO_C3560G_IP') }}"
cisco_username: "{{ lookup('env', 'CISCO_C3560G_USERNAME') }}"
cisco_password: "{{ lookup('env', 'CISCO_C3560G_PASSWORD') }}"
cisco_console_command: "{{ lookup('env', 'CISCO_C3560G_CONSOLE_COMMAND') }}"
cisco_port: 1
```

Vault password sourced from `ANSIBLE_VAULT_PASS` env var (already in `.env`). In GitHub Actions, `ANSIBLE_VAULT_PASS` is a repository secret injected at runtime.

---

## Fixture Targets

Two new integration targets manage DVT3 lifecycle. They are not module tests, they are suite-level setup and teardown.

### `setup_dvt3`

Runs first, before any write-lane target.

1. Pull DVT3 config snapshot via `slc_config` and save as a CI artifact
2. Assert snapshot was retrieved successfully
3. Verify Cisco C3560G is reachable on DVT3 port 1 using `CISCO_C3560G_CONSOLE_COMMAND`
4. Set fact `cisco_port1_available: true/false`
5. If `cisco_port1_available=false`, emit warning: "Cisco C3560G unreachable on port 1, managed device tests will be skipped"

### `teardown_dvt3`

Runs last, unconditionally (`if: always()` in GitHub Actions).

1. Restore the config snapshot captured by `setup_dvt3`
2. Assert restore completed without error
3. Verify DVT3 hostname matches expected value (confirms restore applied)

If `setup_dvt3` never ran (e.g., sanity failed before it), `teardown_dvt3` detects no snapshot artifact and exits cleanly with a warning.

---

## Per-Module Test Structure

Every integration target gets three tiers. Three modules get a fourth.

### Tier 1, Read-Only / Nominal State (DVT)

Existing tests cleaned up and tightened. Verifies:
- All documented return fields are present
- Formats match documented patterns (firmware version regex, hostname non-empty, etc.)
- Read operations always return `changed=false`

No new functional coverage here. This is maintenance of what exists.

### Tier 2, Write Cycle (DVT3)

Applies only to modules with `state=present/absent` or write operations. Five steps in order:

1. **check_mode**, run with `check_mode=true`, assert `changed=true` (for create) or correct value, assert no actual state change occurred
2. **Create**, apply desired state, assert `changed=true`
3. **Idempotency**, apply identical state again, assert `changed=false`
4. **Modify**, change one attribute, assert `changed=true`
5. **Delete/revert**, remove or revert to baseline, assert `changed=true`

Each step has a named assertion block with a `success_msg` and `fail_msg` that identifies the module, step, and what was asserted.

Read-only modules (`slc_facts`, `percepxion_facts`, `percepxion_audit_logs`, `percepxion_telemetry`) have no Tier 2.

### Tier 3, Gap Documentation

At the bottom of every `tasks/main.yml`, a comment block documents untested states:

```yaml
# UNTESTED STATES:
# - <state>: <description of what would need to be triggered and why it's deferred>
```

Example for `slc_firmware`:
```yaml
# UNTESTED STATES:
# - mid-update: /firmware/update_status returns a plain-text log while an update
#   is in progress. Fixed in v1.0.16 (get_firmware_update_status fallback to
#   {"status": "in_progress"}). Testing requires triggering an update and racing
#   the status check, deferred due to device disruption risk.
# - failed-update: /firmware/update_status behavior after a failed update job
#   is undocumented in the API spec. Needs lab verification.
```

The CI pipeline extracts all `# UNTESTED STATES:` blocks and appends them to the GitHub Actions job summary. Every run surfaces the known gap list without digging into logs.

### Tier 4, Managed Device Tests (DVT3, conditional)

Applies to: `slc_managed_devices`, `slc_device_ports`, `percepxion_aoob_session`.

Gated on port 1 availability. Because `ansible-test integration` runs each target in an isolated play, facts set in `setup_dvt3` are not carried over. Each Tier 4 target re-runs the port 1 reachability check at its own start using `CISCO_C3560G_CONSOLE_COMMAND`. If the check fails, the managed device block skips with a message. If it passes, the block runs. This adds a few seconds per target but eliminates inter-target fact dependencies.

**`slc_managed_devices`:**
- Assert Cisco C3560G appears in managed device list
- Assert device attributes (hostname, port number, connection state) match expected values
- Modify a managed device attribute, assert `changed=true`, revert

**`slc_device_ports`:**
- Read port 1 config, assert current baud rate and mode
- Apply a config change (e.g., description field), assert `changed=true`
- Assert idempotency
- Revert description, assert `changed=true`
- Assert port 1 config with live device differs from an unconfigured port (structural comparison)

**`percepxion_aoob_session`:**
- Assert DVT3 device is visible in Percepxion Cisco Live project
- Establish AOOB session to DVT3 → port 1 → Cisco C3560G
- Assert session returns a valid CLI prompt response
- Terminate session, assert clean teardown
- Assert `changed=true` on session open, `changed=true` on session close

---

## GitHub Actions CI Pipeline

**File:** `.github/workflows/integration.yml`

**Triggers:**
- Push to `main`
- `workflow_dispatch` with optional `lane` input: `dvt`, `dvt3`, or `all` (default: `all`)

**Runner:** Self-hosted, on lab network, with access to 192.168.100.75, 192.168.100.76, and `PX_API_BASE_DVT3`.

**Job sequence:**
```
sanity ──► unit ──► setup_dvt3 ──► integration_dvt   ──► teardown_dvt3
                               └─► integration_dvt3  ─┘
```

- `sanity` and `unit` run on GitHub-hosted runner (no lab access needed)
- `setup_dvt3`, `integration_dvt`, `integration_dvt3`, `teardown_dvt3` run on self-hosted runner
- `integration_dvt` and `integration_dvt3` run in parallel, neither blocks the other
- `teardown_dvt3` has `needs: [integration_dvt3]` and `if: always()`
- Any sanity or unit failure short-circuits the whole pipeline before lab access

**Environment variables:**
All `SLC9_*`, `SLC9K_DVT3_*`, `PX_*`, `ANSIBLE_*`, `CISCO_C3560G_*` vars are GitHub repository secrets. The workflow writes them to a `.env` file in the runner workspace at job start.

**CI summary output:**
- Pass/fail table per integration target
- Extracted `# UNTESTED STATES:` blocks appended as "Known Gaps" section
- Firmware versions of DVT and DVT3 logged at suite start (from `slc_facts` output)

---

## Three-Agent Execution Sequence

### Phase 1, Gap Analysis (engineer-reviewer)

Reads all 20 existing integration targets and 20 unit test files. Produces:
`docs/superpowers/analyses/YYYY-MM-DD-collection-test-gap-analysis.md`

Contents:
- Per-module table: current tier coverage, missing Tier 2 steps, recommended `# UNTESTED STATES:` entries
- Priority ranking: which modules have the highest bug risk based on API complexity
- Managed device module assessment: specific scenarios for Tier 4

No code written in Phase 1.

### Phase 2, Parallel Implementation

**devops-engineer** owns infrastructure (no module test files):
- `tests/integration/targets/setup_dvt3/`
- `tests/integration/targets/teardown_dvt3/`
- `integration_config.yml` → vault migration
- `integration_config.yml.example`
- `.github/workflows/integration.yml`
- `docs/self-hosted-runner-setup.md`

**network-engineer** owns module tests (no infrastructure files), informed by gap report:
- Tier 2 write cycles for all 8 SLC modules
- Tier 2 write cycles for all 12 Percepxion modules
- Tier 3 gap markers for all 20 modules
- Tier 4 managed device blocks for `slc_managed_devices`, `slc_device_ports`, `percepxion_aoob_session`

The two agents share no files. Merge conflicts are not possible.

### Phase 3, Audit (engineer-reviewer)

Reads finished suite against four criteria:
1. Every write module has all four Tier 2 steps (check_mode → create → idempotency → modify → delete)
2. Every module has a `# UNTESTED STATES:` block (even if it just says "none identified")
3. `teardown_dvt3` leaves no test artifacts on the device
4. GitHub Actions workflow `teardown_dvt3` has `if: always()`

Produces sign-off checklist. Failures go back to the Phase 2 agent that owns that file.

---

## Definition of Done

- [ ] All 20 integration targets pass `ansible-test integration` against DVT (read-only lane)
- [ ] All write-capable modules pass Tier 2 cycle against DVT3
- [ ] DVT3 config matches pre-test baseline after `teardown_dvt3` runs
- [ ] Cisco C3560G managed device tests pass (or skip cleanly if port 1 unreachable)
- [ ] `integration_config.yml` contains no plaintext credentials
- [ ] GitHub Actions pipeline passes end-to-end on self-hosted runner
- [ ] Known gaps summary visible in CI run output
- [ ] `galaxy.yml` version bumped to `1.0.16`
- [ ] engineer-reviewer Phase 3 sign-off checklist complete
