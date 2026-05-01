#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_facts
short_description: Gather facts from a Lantronix SLC 9000 device
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Retrieves hardware version, software version, system status, and identity
    information from an SLC 9000 device via REST API v2.
  - Combines output from /system/version, /system/status, and /system/identity
    into a single C(slc_facts) dict.
notes:
  - Requires C(ansible_network_os=lantronix.oob.slc9) and
    C(ansible_connection=ansible.netcommon.httpapi).
"""

EXAMPLES = r"""
- name: Gather SLC 9000 facts
  lantronix.oob.slc_facts:
  register: result

- name: Show firmware version
  ansible.builtin.debug:
    msg: "Firmware: {{ result.slc_facts.current_firmware_version }}"

- name: Alert on high temperature
  ansible.builtin.debug:
    msg: "High temperature: {{ result.slc_facts.temperature }}"
  when: result.slc_facts.temperature | int > 70
"""

RETURN = r"""
slc_facts:
  description: Combined hardware, software, status, and identity information.
  returned: always
  type: dict
  contains:
    model:
      description: SLC hardware model string.
      type: str
      sample: SLC9032
    current_firmware_version:
      description: Firmware version running on the active boot bank.
      type: str
      sample: 9.7.0.0R8
    bootloader_version:
      description: Bootloader version installed on the device.
      type: str
      sample: 1.0.0.0R19
    sw_python_version:
      description: Python interpreter version bundled with the firmware.
      type: str
      sample: 3.13.2
    sw_kernel_version:
      description: Linux kernel version running on the device.
      type: str
      sample: 6.6.52
    io_module_types:
      description: Comma-separated list of I/O module types installed.
      type: str
      sample: "RJ45-16, USB-16, ETH-16"
    uptime:
      description: Device uptime in seconds.
      type: int
      sample: 34060479
    temperature:
      description: Internal temperature in Celsius.
      type: int
      sample: 58
    eth1_link:
      description: Ethernet port 1 link state.
      type: str
      sample: Up
    eth2_link:
      description: Ethernet port 2 link state.
      type: str
      sample: Up
    ps1:
      description: Power supply 1 status.
      type: str
      sample: Ok
    ps2:
      description: Power supply 2 status.
      type: str
      sample: Ok
    hostname:
      description: Configured device hostname.
      type: str
      sample: slc9k-lab
    description:
      description: User-configured device description.
      type: str
      sample: Lab console server
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(argument_spec={}, supports_check_mode=True)

    connection = Connection(module._socket_path)
    token = connection.get_token()
    host = connection.get_option("host")

    client = SLC9Client(host=host, token=token, verify_ssl=connection.get_option("validate_certs"))

    try:
        version = client.get_system_version()
        status = client.get_system_status()
        identity = client.get_system_identity()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))
        return

    facts = {}
    facts.update(version)
    facts.update(status)
    facts.update(identity)

    module.exit_json(changed=False, slc_facts=facts)


if __name__ == "__main__":
    main()
