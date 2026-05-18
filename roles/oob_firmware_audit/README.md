# oob_firmware_audit

Checks firmware compliance across a Percepxion smart group and optionally triggers upgrades for non-compliant devices.

## Requirements

- `lantronix.oob.percepxion_firmware` module
- Percepxion connection configured in inventory (`ansible_network_os: lantronix.oob.percepxion`)

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `oob_firmware_audit_smart_group_id` | `""` | Percepxion smart group ID to audit. Required. |
| `oob_firmware_audit_target_version` | `""` | Target firmware version string (e.g. `9.7.0.0R8`). Required. |
| `oob_firmware_audit_remediate` | `false` | Set to `true` to trigger upgrades on non-compliant devices. |

## Example Playbook

```yaml
- hosts: percepxion
  gather_facts: false
  roles:
    - role: lantronix.oob.oob_firmware_audit
      vars:
        oob_firmware_audit_smart_group_id: sg-datacenter-slc
        oob_firmware_audit_target_version: 9.7.0.0R8
        oob_firmware_audit_remediate: false
```
