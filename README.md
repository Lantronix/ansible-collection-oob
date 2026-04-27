# lantronix.oob Ansible Collection

Manage Lantronix Out-of-Band infrastructure from Ansible.

## Installation

    ansible-galaxy collection install lantronix.oob

## Requirements

- ansible-core >= 2.14
- ansible.netcommon >= 5.0.0
- Python requests library (`pip install requests`)

## Supported Platforms

| Platform | Connection | API |
|---|---|---|
| SLC 9000 | `ansible.netcommon.httpapi` | REST API v2 (OpenAPI 3.1.0) |
| Percepxion 6.12+ | `ansible.netcommon.httpapi` | OpenAPI 3.0.1 |

## Quick Start

```yaml
# inventory.yml
slc9_devices:
  hosts:
    slc9k-lab:
      ansible_host: 192.0.2.1
  vars:
    ansible_network_os: lantronix.oob.slc9
    ansible_connection: ansible.netcommon.httpapi
    ansible_httpapi_use_ssl: true
    ansible_httpapi_validate_certs: false

percepxion:
  hosts:
    percepxion_platform:
      ansible_host: api.consoleflow.com
  vars:
    ansible_network_os: lantronix.oob.percepxion
    ansible_connection: ansible.netcommon.httpapi
    ansible_httpapi_use_ssl: true
    percepxion_project_tag: "your-project"
```

```yaml
# playbook.yml
- hosts: slc9_devices
  gather_facts: false
  tasks:
    - name: Get device facts
      lantronix.oob.slc_facts:
      register: result
    - debug:
        var: result.slc_facts
```
