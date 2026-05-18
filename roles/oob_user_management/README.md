# oob_user_management

Manages local user accounts across SLC9000 devices. Applies a defined user list idempotently, adding, updating, or removing accounts as needed.

## Requirements

- `lantronix.oob.slc_users` module
- SLC9000 connection configured in inventory (`ansible_network_os: lantronix.oob.slc9`)

## Role Variables

| Variable | Default | Description |
|---|---|---|
| `oob_user_management_users` | `[]` | List of user objects to manage. Each entry supports `username`, `password`, `role` (`user` or `admin`), and `state` (`present` or `absent`). |
| `oob_user_management_target_group` | `""` | Optional label for the target device group. Informational only. |

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
            state: present
          - username: readonly
            password: "{{ vault_readonly_password }}"
            role: user
            state: present
          - username: olduser
            state: absent
```
