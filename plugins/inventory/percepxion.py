from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
---
name: percepxion
short_description: Build an inventory of Lantronix devices from Percepxion
version_added: "1.5.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Reads the devices a Percepxion account can see and adds each one as a host, with its
    management address as C(ansible_host) and its Percepxion details as host variables.
  - Console managers (SLC 8000, SLC 9000, EMG) are placed in C(percepxion_console_managers) and in
    a group per family (C(percepxion_slc8000), C(percepxion_slc9000), C(percepxion_emg)), ready for
    modules such as M(lantronix.oob.slc_groups) over SSH or M(lantronix.oob.percepxion_slc_groups).
  - Uses a YAML configuration file that ends in C(percepxion.yml) or C(percepxion.yaml).
extends_documentation_fragment:
  - ansible.builtin.constructed
  - ansible.builtin.inventory_cache
options:
  plugin:
    description: Marks this file as configuration for this plugin.
    type: str
    required: true
    choices: [lantronix.oob.percepxion]
  api_host:
    description: Percepxion API host name.
    type: str
    default: api.percepxion.ai
    env:
      - name: LANTRONIX_PERCEPXION_HOST
  username:
    description: Percepxion user name.
    type: str
    required: true
    env:
      - name: LANTRONIX_PERCEPXION_USERNAME
  password:
    description: Percepxion password.
    type: str
    required: true
    env:
      - name: LANTRONIX_PERCEPXION_PASSWORD
  tenant_id:
    description: Organization (tenant) ID. Needed when the account is a Project Admin.
    type: str
  validate_certs:
    description: Verify the Percepxion TLS certificate.
    type: bool
    default: true
  search_string:
    description: Percepxion device search text. C(*) returns every device the account can see.
    type: str
    default: "*"
  families:
    description:
      - Only add devices of these families. Empty adds every device.
      - Families are C(slc8000), C(slc9000), C(emg) and C(other).
    type: list
    elements: str
    default: []
  connected_only:
    description: Only add devices that Percepxion currently reports as connected.
    type: bool
    default: false
  address_attributes:
    description: Device attributes to try, in order, for C(ansible_host).
    type: list
    elements: str
    default: [ipaddress, eth1_ipv4address, eth2_ipv4address]
  hostname_source:
    description: Device field used as the inventory host name.
    type: str
    default: device_name
    choices: [device_name, device_id]
  page_size:
    description: Devices requested per page.
    type: int
    default: 200
  timeout:
    description: Seconds to wait for each Percepxion request.
    type: int
    default: 60
"""

EXAMPLES = r"""
# percepxion.yml
plugin: lantronix.oob.percepxion
api_host: api.percepxion.ai
families: [slc8000, slc9000, emg]
connected_only: true
compose:
  ansible_network_os: "'lantronix.oob.slc'"
  ansible_connection: "'ansible.netcommon.network_cli'"
keyed_groups:
  - key: percepxion_firmware
    prefix: firmware
"""

import json
import re

from ansible.errors import AnsibleError, AnsibleParserError
from ansible.module_utils.common.text.converters import to_native
from ansible.module_utils.urls import open_url
from ansible.plugins.inventory import BaseInventoryPlugin, Cacheable, Constructable

CONSOLE_MANAGER_TYPE = "ltrx_itm"
FAMILY_PATTERNS = (
    ("slc8000", re.compile(r"^SLC80", re.I)),
    ("slc9000", re.compile(r"^SLC90", re.I)),
    ("emg", re.compile(r"^EMG", re.I)),
)
MAX_PAGES = 500


def device_family(model):
    for family, pattern in FAMILY_PATTERNS:
        if pattern.match(model or ""):
            return family
    return "other"


def device_address(attributes, keys):
    for key in keys:
        value = (attributes or {}).get(key)
        if value:
            return str(value).split("/", maxsplit=1)[0]
    return None


def host_vars(device, address_keys):
    attributes = device.get("attributes") or {}
    model = attributes.get("model") or ""
    variables = {
        "percepxion_device_id": device.get("device_id"),
        "percepxion_device_name": device.get("device_name"),
        "percepxion_serial": device.get("serial_num"),
        "percepxion_model": model,
        "percepxion_family": device_family(model),
        "percepxion_firmware": attributes.get("firmware_ver"),
        "percepxion_status": device.get("status"),
        "percepxion_last_contacted": device.get("last_contacted"),
        "percepxion_project_tag": device.get("project_tag"),
        "percepxion_organizations": [t.get("name") for t in device.get("tenant") or [] if t.get("name")],
        "percepxion_console_manager": device.get("dev_type") == CONSOLE_MANAGER_TYPE,
    }
    address = device_address(attributes, address_keys)
    if address:
        variables["ansible_host"] = address
    return variables


class InventoryModule(BaseInventoryPlugin, Constructable, Cacheable):

    NAME = "lantronix.oob.percepxion"

    def verify_file(self, path):
        return super(InventoryModule, self).verify_file(path) and path.endswith(
            ("percepxion.yml", "percepxion.yaml"))

    def _request(self, path, body, headers=None):
        all_headers = {"Content-Type": "application/json", "Accept": "application/json"}
        all_headers.update(headers or {})
        try:
            resp = open_url(
                "https://{0}/api{1}".format(self.get_option("api_host"), path),
                data=json.dumps(body), headers=all_headers, method="POST",
                validate_certs=self.get_option("validate_certs"), timeout=self.get_option("timeout"),
            )
            return json.loads(resp.read() or b"{}")
        except Exception as exc:
            raise AnsibleError("Percepxion request {0} failed: {1}".format(path, to_native(exc)))

    def _fetch_devices(self):
        login = self._request("/v2/user/login", {
            "username": self.get_option("username"), "password": self.get_option("password")})
        if not login.get("token"):
            raise AnsibleError("Percepxion login returned no token")
        headers = {"x-mystq-token": login["token"], "x-csrf-token": login.get("csrf_token", "")}
        page_size = self.get_option("page_size")
        devices, after = [], None
        for dummy in range(MAX_PAGES):
            body = {"search_string": self.get_option("search_string"), "limit": page_size,
                    "sort": "device_name", "order": "asc"}
            if self.get_option("tenant_id"):
                body["tenant_id"] = self.get_option("tenant_id")
            if after:
                body.update(search_after=after, pagination="next")
            page = self._request("/v3/device/search", body, headers)
            results = page.get("search_results") or []
            devices.extend(results)
            after = page.get("sort_last")
            if not results or len(results) < page_size or not after:
                break
        return devices

    def _populate(self, devices):
        families = [f.lower() for f in self.get_option("families")]
        connected_only = self.get_option("connected_only")
        address_keys = self.get_option("address_attributes")
        strict = self.get_option("strict")
        self.inventory.add_group("percepxion_console_managers")
        for device in devices:
            variables = host_vars(device, address_keys)
            if families and variables["percepxion_family"] not in families:
                continue
            if connected_only and str(variables["percepxion_status"]).lower() != "connected":
                continue
            name = device.get(self.get_option("hostname_source")) or device.get("device_id")
            if not name:
                continue
            self.inventory.add_host(name)
            for key, value in variables.items():
                self.inventory.set_variable(name, key, value)
            if variables["percepxion_console_manager"]:
                self.inventory.add_child("percepxion_console_managers", name)
            family_group = "percepxion_" + variables["percepxion_family"]
            self.inventory.add_group(family_group)
            self.inventory.add_child(family_group, name)
            self._set_composite_vars(self.get_option("compose"), variables, name, strict=strict)
            self._add_host_to_composed_groups(self.get_option("groups"), variables, name, strict=strict)
            self._add_host_to_keyed_groups(self.get_option("keyed_groups"), variables, name, strict=strict)

    def parse(self, inventory, loader, path, cache=True):
        super(InventoryModule, self).parse(inventory, loader, path, cache)
        self._read_config_data(path)
        cache_key = self.get_cache_key(path)
        use_cache = self.get_option("cache") and cache
        update_cache = self.get_option("cache") and not cache
        devices = None
        if use_cache:
            try:
                devices = self._cache[cache_key]
            except KeyError:
                update_cache = True
        if devices is None:
            devices = self._fetch_devices()
        if update_cache:
            self._cache[cache_key] = devices
        try:
            self._populate(devices)
        except Exception as exc:
            raise AnsibleParserError("Failed to build the Percepxion inventory: {0}".format(to_native(exc)))
