# Self-Hosted Runner Setup

The integration tests against physical lab devices require a GitHub Actions
self-hosted runner on the lab network.

## Requirements

- Ubuntu 22.04 or later
- Python 3.11
- `ansible-core` and `ansible.netcommon` installed
- Network access to the SLC9000 lab devices and Percepxion API
- Outbound HTTPS to GitHub Actions endpoints

## Installation

Follow the GitHub Actions self-hosted runner installation guide for your
repository. Then install the Ansible dependencies:

```bash
sudo apt install -y gettext  # provides envsubst, used by the workflow for config injection
pip install ansible-core requests
ansible-galaxy collection install ansible.netcommon
```

## Required Repository Secrets

Add these as GitHub repository secrets before running integration tests.
Navigate to: **Settings -> Secrets and variables -> Actions -> New repository secret**

### Read-Only Lane

| Secret | Description |
|---|---|
| `SLC9_IP` | SLC9000 management IP address |
| `SLC9_USER` | SLC9000 username |
| `SLC9_PASSWORD` | SLC9000 password |
| `SLC9_HOSTNAME` | Expected hostname (used by teardown to verify restore) |
| `PX_API_BASE` | Percepxion API base URL (primary project) |
| `PX_PROJECT_USER` | Percepxion username (primary project) |
| `PX_PROJECT_PASSWORD` | Percepxion password (primary project) |

### Write Lane

| Secret | Description |
|---|---|
| `SLC9K_DVT3_IP` | SLC9000 write-lane device IP |
| `SLC9K_DVT3_USER` | SLC9000 write-lane username |
| `SLC9K_DVT3_PASSWORD` | SLC9000 write-lane password |
| `SLC9K_DVT3_HOSTNAME` | Write-lane expected hostname |
| `PX_API_BASE_DVT3` | Percepxion API base URL (write project) |
| `PX_URL_DVT3` | Percepxion web UI URL (write project) |
| `PX_PROJECT_USER_DVT3` | Percepxion username (write project) |
| `PX_PROJECT_PASSWORD_DVT3` | Percepxion password (write project) |
| `PX_PORTAL_NAME_DVT3` | Percepxion portal name |
| `PX_ORG_NAME_DVT3` | Percepxion organization name |

### Managed Device (Optional -- Tier 4 Tests)

| Secret | Description |
|---|---|
| `MANAGED_DEVICE_IP` | Managed device management IP |
| `MANAGED_DEVICE_USERNAME` | Managed device username |
| `MANAGED_DEVICE_PASSWORD` | Managed device password |
| `MANAGED_DEVICE_CONSOLE_COMMAND` | SSH command reaching the device via console server port 1 |

If the managed device secrets are not set, the reachability check
in `setup_dvt3` will fail. The Tier 4 tests will be skipped cleanly.

## Running Manually

```bash
# Read-only lane only
gh workflow run integration.yml -f lane=read

# Write lane only
gh workflow run integration.yml -f lane=write

# Full suite (default)
gh workflow run integration.yml
```

## Local Development

For running integration tests locally without GitHub Actions:

1. Copy `tests/integration/integration_config.yml.example` to
   `tests/integration/integration_config.yml`
2. Fill in real values (this file is gitignored)
3. Run a specific target:
   ```bash
   ansible-test integration slc_facts --python 3.11
   ```
4. Run all read-only targets:
   ```bash
   ansible-test integration slc_facts slc_firmware slc_system ... --python 3.11
   ```
