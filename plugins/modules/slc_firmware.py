#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
module: slc_firmware
short_description: Check firmware version or trigger a firmware update on SLC9000
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
  md5_key:
    description: MD5 checksum string provided by Lantronix alongside the firmware download. Required when C(state=update).
    type: str
  reboot_after_update:
    description: Reboot the device automatically after the firmware image is written to the alternate bank.
    type: bool
    default: false
  description:
    description: Optional label stored in the firmware update job record.
    type: str
    default: ""
"""

EXAMPLES = r"""
- name: Check current firmware version
  lantronix.oob.slc_firmware:
    state: check
  register: result

- name: Show installed version
  debug:
    msg: "Firmware: {{ result.firmware.current_firmware_version }}"

- name: Trigger firmware update (no immediate reboot)
  lantronix.oob.slc_firmware:
    state: update
    url: "http://fileserver.example.com/firmware/slc9update-9.8.0.0R1.tgz"
    md5_key: "{{ vault_fw_md5_key }}"
    description: "Upgrade to 9.8.0.0R1"
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
            md5_key=dict(type="str", no_log=True),
            reboot_after_update=dict(type="bool", default=False),
            description=dict(type="str", default=""),
        ),
        required_if=[("state", "update", ["url", "md5_key"])],
        supports_check_mode=True,
    )

    connection = Connection(module._socket_path)
    client = SLC9Client(host=connection.get_option("host"), token=connection.get_token(), verify_ssl=connection.get_option("validate_certs"))

    try:
        status = client.get_firmware_status()
        update_status = client.get_firmware_update_status()
    except AnsibleLantronixError as exc:
        module.fail_json(msg=str(exc))

    firmware_info = {
        "current_firmware_version": status.get("current_firmware_version", ""),
        "alternate_firmware_version": status.get("alternate_firmware_version", ""),
        "active_bank": "bank{0}".format(status.get("current_boot_bank", "")),
        "update_status": update_status.get("status", ""),
        "update_progress": update_status.get("progress", 0),
    }

    if module.params["state"] == "check":
        module.exit_json(changed=False, firmware=firmware_info)
        return

    if not module.check_mode:
        try:
            client.trigger_firmware_update(
                file_url=module.params["url"],
                md5_key=module.params["md5_key"],
                reboot_after_update=module.params["reboot_after_update"],
                description=module.params.get("description") or "",
            )
        except AnsibleLantronixError as exc:
            module.fail_json(msg=str(exc))

    module.exit_json(changed=True, firmware=firmware_info)


if __name__ == "__main__":
    main()
