# oob_baseline_config

Enforces baseline hostname, NTP, and syslog configuration across SLC9000 devices.

## Requirements

- `lantronix.oob.slc_system` module
- `lantronix.oob.slc_config` module
- SLC9000 connection configured in inventory (`ansible_network_os: lantronix.oob.slc9`)

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `oob_baseline_config_hostname` | `""` | Hostname to set on the device. Skipped if empty. |
| `oob_baseline_config_ntp_servers` | `[]` | List of NTP server addresses to configure. |
| `oob_baseline_config_syslog_host` | `""` | Syslog server address. Skipped if empty. |

## Example Playbook

```yaml
- hosts: slc_devices
  gather_facts: false
  roles:
    - role: lantronix.oob.oob_baseline_config
      vars:
        oob_baseline_config_hostname: dc1-slc9k-01
        oob_baseline_config_ntp_servers:
          - 192.168.1.10
          - 192.168.1.11
        oob_baseline_config_syslog_host: 192.168.1.50
```
