# oob_fleet_inventory

Queries Percepxion for all managed devices and writes a dynamic Ansible inventory file.

## Requirements

- `lantronix.oob.percepxion_devices` module
- Percepxion connection configured in inventory (`ansible_network_os: lantronix.oob.percepxion`)

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `oob_inventory_output_path` | `/tmp/oob-inventory.yml` | Path to write the generated inventory file |
| `oob_inventory_search_string` | `""` | Optional device name filter |
| `oob_inventory_limit` | `500` | Maximum devices to fetch |

## Example Playbook

```yaml
- hosts: percepxion
  gather_facts: false
  roles:
    - role: lantronix.oob.oob_fleet_inventory
      vars:
        oob_inventory_output_path: /etc/ansible/oob-inventory.yml
        oob_inventory_limit: 1000
```
