# lantronix.oob.oob_slc_groups

Keeps directory-mapped custom user groups identical on SLC 8000, SLC 9000 and EMG console managers. A custom group whose name matches an LDAP or Active Directory group sets the ports and rights that group's members get, so one definition applied everywhere means the same access on every console manager.

Each host is changed over SSH (`lantronix.oob.slc_groups`) or through Percepxion (`lantronix.oob.percepxion_slc_groups`), chosen per host with `oob_slc_groups_transport`.

| Transport | Use when | Notes |
|---|---|---|
| `ssh` (default) | The control node can reach the console manager over SSH | Seconds per host, all models, deletes groups directly |
| `percepxion` | Only Percepxion can reach the console manager | One Percepxion job for all such hosts, a few minutes per step. Needs firmware that returns CLI output to Percepxion. Removes groups by revoking them |

## Example

```yaml
# inventory/fleet.percepxion.yml builds the hosts from Percepxion
# group_vars/percepxion_console_managers.yml holds SSH credentials (Ansible Vault)
- name: Keep OOB access groups consistent
  hosts: percepxion_console_managers
  gather_facts: false
  vars:
    oob_slc_groups_percepxion_host: percepxion_platform   # only needed for the percepxion transport
    oob_slc_groups_definitions:
      - name: OOB-Read
        data_ports: ALL
        listen_ports: ALL
        clear_ports: ALL
        rights: [sv, do]
      - name: OOB-Admin
        data_ports: ALL
        listen_ports: ALL
        clear_ports: ALL
        rights: [ad, nt, sv, dt, lu, ra, um, dp, ub, rs, fc, dr, sn, wb, sk, do, sd, md, rp, sw]
  roles:
    - lantronix.oob.oob_slc_groups
```

Set `oob_slc_groups_transport: percepxion` in host or group variables for console managers without an SSH path. The Percepxion API host must be in the inventory with `ansible_network_os: lantronix.oob.percepxion`.

## Variables

See `meta/argument_specs.yml`. Results are registered as `oob_slc_groups_ssh_result` (per host) and `oob_slc_groups_percepxion_result` (once, for all Percepxion hosts). The Percepxion step runs once per play, so Ansible reports its change under the first host in the play; per-device outcomes are in `oob_slc_groups_percepxion_result.devices`.
