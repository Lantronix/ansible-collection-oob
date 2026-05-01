#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_firmware
short_description: Check firmware version or trigger a firmware update on SLC 9000
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - When C(state=check), returns current and alternate firmware versions plus
    update status. Always C(changed=False).
  - When C(state=update), posts a firmware update request to the device. Always
    C(changed=True). The device downloads and installs the image asynchronously;
    poll C(state=check) to track progress.
notes:
  - Firmware updates are non-idempotent. Running C(state=update) always triggers
    a new update job regardless of the currently installed version.
  - The device may reboot automatically after the update completes depending on
    firmware settings.
options:
  state:
    description:
      - C(check) returns version and update status without making changes.
      - C(update) submits a firmware update request using C(url).
    type: str
    required: true
    choices: [check, update]
  url:
    description: URL of the firmware image to install. Required when C(state=update).
    type: str
  bank:
    description: Boot bank to write the firmware into. When omitted, the device chooses.
    type: str
    choices: [active, alternate]
"""

EXAMPLES = r"""
- name: Check current firmware version
  lantronix.oob.slc_firmware:
    state: check
  register: result

- name: Show installed version
  debug:
    msg: "Firmware: {{ result.firmware.current_firmware_version }}"

- name: Trigger firmware update to alternate bank
  lantronix.oob.slc_firmware:
    state: update
    url: "https://downloads.lantronix.com/firmware/slc9000-9.8.0.0R1.bin"
    bank: alternate
"""

RETURN = r"""
firmware:
  description: Firmware version and update status information.
  returned: always
  type: dict
  contains:
    current_firmware_version:
      description: Version running on the active boot bank.
      type: str
      sample: 9.7.0.0R8
    alternate_firmware_version:
      description: Version installed on the alternate boot bank.
      type: str
      sample: 9.6.0.0R5
    active_bank:
      description: Which bank is currently active.
      type: str
      sample: bank1
    update_status:
      description: Current update job status (idle, in_progress, complete, failed).
      type: str
      sample: idle
    update_progress:
      description: Update progress percentage (0-100).
      type: int
      sample: 0
"""

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.connection import Connection
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", required=True, choices=["check", "update"]),
            url=dict(type="str"),
            bank=dict(type="str", choices=["active", "alternate"]),
        ),
        required_if=[("state", "update", ["url"])],
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token(), verify_ssl=connection.get_option("validate_certs"))

    try:
        version = client.get_firmware_version()
        update_status = client.get_firmware_update_status()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    firmware_info = dict(version)
    firmware_info["update_status"] = update_status.get("status", "")
    firmware_info["update_progress"] = update_status.get("progress", 0)

    if module.params["state"] == "check":
        module.exit_json(changed=False, firmware=firmware_info)
        return

    if not module.check_mode:
        try:
            client.trigger_firmware_update(module.params["url"], bank=module.params.get("bank"))
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))

    module.exit_json(changed=True, firmware=firmware_info)


if __name__ == "__main__":
    main()
