#!/usr/bin/env python3
"""Generate a static Ansible YAML inventory from integration_config.yml.

Uses YAML format so special characters in passwords (e.g. #, !, ^) are
not misinterpreted as INI comment or shell metacharacters.

Usage: python3 gen_inventory.py [output_path]
Default output: /tmp/oob-lab-inventory
"""
from __future__ import absolute_import, division, print_function

import os
import sys
import yaml


def main():
    config_path = os.path.join(os.path.dirname(__file__), "integration_config.yml")
    output_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/oob-lab-inventory"

    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    inventory = {
        "all": {
            "hosts": {
                "localhost": {
                    "ansible_connection": "local",
                }
            },
            "children": {
                "slc_read": {
                    "hosts": {
                        "slc9000": {
                            "ansible_host": cfg["slc_read_host"],
                            "ansible_user": cfg["slc_read_username"],
                            "ansible_password": cfg["slc_read_password"],
                            "ansible_network_os": "lantronix.oob.slc9",
                            "ansible_connection": "ansible.netcommon.httpapi",
                            "ansible_httpapi_use_ssl": True,
                            "ansible_httpapi_validate_certs": False,
                        }
                    }
                },
                "slc_write": {
                    "hosts": {
                        "slc9000-write": {
                            "ansible_host": cfg["slc_write_host"],
                            "ansible_user": cfg["slc_write_username"],
                            "ansible_password": cfg["slc_write_password"],
                            "ansible_network_os": "lantronix.oob.slc9",
                            "ansible_connection": "ansible.netcommon.httpapi",
                            "ansible_httpapi_use_ssl": True,
                            "ansible_httpapi_validate_certs": False,
                        }
                    }
                },
                "percepxion_read": {
                    "hosts": {
                        "percepxion-primary": {
                            "ansible_host": cfg["percepxion_read_host"],
                            "ansible_user": cfg["percepxion_read_username"],
                            "ansible_password": cfg["percepxion_read_password"],
                            "ansible_network_os": "lantronix.oob.percepxion",
                            "ansible_connection": "ansible.netcommon.httpapi",
                            "ansible_httpapi_use_ssl": True,
                            "ansible_httpapi_validate_certs": True,
                            "percepxion_tenant_id": cfg.get("percepxion_read_tenant_id") or cfg.get("percepxion_tenant_id") or None,
                        }
                    }
                },
                "percepxion_write": {
                    "hosts": {
                        "percepxion-write": {
                            "ansible_host": cfg["percepxion_host"],
                            "ansible_user": cfg["percepxion_username"],
                            "ansible_password": cfg["percepxion_password"],
                            "ansible_network_os": "lantronix.oob.percepxion",
                            "ansible_connection": "ansible.netcommon.httpapi",
                            "ansible_httpapi_use_ssl": True,
                            "ansible_httpapi_validate_certs": True,
                            "percepxion_tenant_id": cfg.get("percepxion_write_tenant_id") or cfg.get("percepxion_tenant_id") or None,
                            "percepxion_project_tag": cfg.get("percepxion_write_project_tag") or None,
                        }
                    }
                },
            }
        }
    }

    with open(output_path, "w") as f:
        yaml.dump(inventory, f, default_flow_style=False, allow_unicode=True)

    print("Inventory written to: {}".format(output_path))


if __name__ == "__main__":
    main()
