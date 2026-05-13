# oob_baseline_config

Applies a baseline configuration to SLC devices: hostname, NTP servers, and syslog host.

## Requirements

- `lantronix.oob.slc_system` and `lantronix.oob.slc_config` modules
- SLC device connection configured in inventory (`ansible_network_os: lantronix.oob.slc9`)

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `oob_baseline_config_hostname` | `""` | Device hostname to set (skipped if empty) |
| `oob_baseline_config_ntp_servers` | `[]` | List of NTP server addresses |
| `oob_baseline_config_syslog_host` | `""` | Syslog server address (skipped if empty) |

## Example Playbook

```yaml
- hosts: slc_devices
  gather_facts: false
  roles:
    - role: lantronix.oob.oob_baseline_config
      vars:
        oob_baseline_config_hostname: slc-datacenter-01
        oob_baseline_config_ntp_servers:
          - 192.168.1.10
          - 192.168.1.11
        oob_baseline_config_syslog_host: 192.168.1.20
```
