# oob_user_management

Ensures local user accounts are configured on SLC devices.

## Requirements

- `lantronix.oob.slc_users` module
- SLC device connection configured in inventory (`ansible_network_os: lantronix.oob.slc9`)

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `oob_user_management_users` | `[]` | List of user objects to configure |
| `oob_user_management_target_group` | `""` | Optional inventory group to target (informational) |

Each user object supports:

| Key | Required | Description |
|---|---|---|
| `username` | yes | Login name |
| `password` | no | Password (omitted if not set) |
| `role` | no | `admin` or `user` (default: `user`) |
| `state` | no | `present` or `absent` (default: `present`) |

## Example Playbook

```yaml
- hosts: slc_devices
  gather_facts: false
  roles:
    - role: lantronix.oob.oob_user_management
      vars:
        oob_user_management_users:
          - username: netops
            password: "{{ vault_netops_password }}"
            role: admin
          - username: readonly
            role: user
```
