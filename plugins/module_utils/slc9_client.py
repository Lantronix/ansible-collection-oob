from __future__ import absolute_import, division, print_function
__metaclass__ = type

import time

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

from ansible_collections.lantronix.oob.plugins.module_utils.common import api_error_message, AnsibleLantronixError


class SLC9Client:
    """Thin REST client for SLC9000 API v2.

    Instantiate with host and token obtained from the httpapi plugin.
    Modules never import requests directly -- they call methods on this class.
    """

    BASE_PATH = "/api/v2"

    def __init__(self, host, token, verify_ssl=True):
        self.host = host
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-auth-token": token,
        })
        self.session.verify = verify_ssl

    def _url(self, path):
        return "https://{0}{1}{2}".format(self.host, self.BASE_PATH, path)

    def _get(self, path):
        try:
            resp = self.session.get(self._url(path))
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))
        except ValueError as exc:
            raise AnsibleLantronixError(
                "Invalid JSON from {0} (HTTP {1}): {2}, body: {3!r}".format(
                    path, resp.status_code, exc, resp.text[:200]
                )
            )

    def _post(self, path, data=None):
        try:
            kwargs = {"json": data} if data is not None else {}
            resp = self.session.post(self._url(path), **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

    def _put(self, path, data=None):
        try:
            kwargs = {"json": data} if data is not None else {}
            resp = self.session.put(self._url(path), **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

    def _patch(self, path, data=None):
        try:
            kwargs = {"json": data} if data is not None else {}
            resp = self.session.patch(self._url(path), **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

    # --- System ---

    def get_system_version(self):
        """GET /system/version -- hardware/software version info."""
        return self._get("/system/version")

    def get_system_status(self):
        """GET /system/status -- uptime, link states, power supplies, temp."""
        return self._get("/system/status")

    def get_system_identity(self):
        """GET /system/identity -- hostname and description."""
        return self._get("/system/identity")

    def set_system_identity(self, hostname=None, description=None):
        """POST /system/identity -- update hostname or description.

        The device reloads a subsystem after applying identity changes, which
        causes the HTTP connection to drop before a response is sent. We catch
        that ConnectionError and verify success with a follow-up GET.

        The API field for description is 'site_tag'; this method maps the
        'description' parameter to that key in the request payload.
        """
        payload = {}
        if hostname is not None:
            payload["hostname"] = hostname
        if description is not None:
            payload["site_tag"] = description
        try:
            # Use a short timeout: the device drops the TCP connection (active close
            # or read timeout) immediately after applying identity changes, before
            # sending an HTTP response. Either ConnectionError or ReadTimeout is expected.
            resp = self.session.post(self._url("/system/identity"), json=payload, timeout=5)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            # Device closes the connection after applying identity changes.
            # Wait briefly for the subsystem reload, then verify via GET.
            time.sleep(2)
            return self.get_system_identity()

    # --- Users ---

    def get_sysadmin(self):
        """GET /users/sysadmin -- return sysadmin user attributes."""
        return self._get("/users/sysadmin")

    def set_sysadmin_password(self, new_password):
        """PATCH /users/sysadmin -- change the sysadmin account password."""
        return self._patch("/users/sysadmin", {"new_password": new_password})

    # --- Network ---

    def get_network_interfaces(self):
        """GET /network/interfaces -- ethernet interface config."""
        return self._get("/network/interfaces")

    def set_network_interfaces(self, payload):
        """PUT /network/interfaces -- update interface config."""
        return self._put("/network/interfaces", payload)

    # --- Ports ---

    def get_ports(self):
        """GET /ports -- serial/device port list."""
        return self._get("/ports")

    def get_connections(self):
        """GET /connections -- active port connections."""
        return self._get("/connections")

    # --- Managed Devices ---

    def get_managed_devices(self):
        """GET /managed_devices -- devices discovered on serial ports."""
        return self._get("/managed_devices")

    # --- Firmware ---

    def get_firmware_status(self):
        """GET /firmware/status -- current/alternate boot bank versions and last update result."""
        return self._get("/firmware/status")

    def get_firmware_update_status(self):
        """GET /firmware/update_status -- ongoing update progress."""
        return self._get("/firmware/update_status")

    def trigger_firmware_update(self, file_url, md5_key, reboot_after_update=False, description=""):
        """POST /firmware/update -- start a firmware update from URL.

        Despite the OpenAPI spec listing multipart/form-data, the SLC accepts
        plain JSON. Firmware is always written to the alternate boot bank.
        """
        payload = {
            "file_url": file_url,
            "key": md5_key,
            "reboot_after_update": reboot_after_update,
            "description": description,
        }
        return self._post("/firmware/update", payload)

    # --- Config ---

    def get_config_commands(self):
        """GET /config/commands -- current running config as CLI commands."""
        return self._get("/config/commands")

    def compare_config(self):
        """GET /config/compare -- diff running vs saved config."""
        return self._get("/config/compare")

    def save_config(self, config_record=None):
        """POST /config/save -- save one or more config groups to flash.

        Pass a list of config group dicts (see ConfigSaveRequest schema).
        An empty list is valid and returns 200 with 0 groups saved.
        """
        return self._post("/config/save", {"config_record": config_record or []})

    def post_config_batch(self, commands):
        """POST /config/batch -- execute a list of CLI config commands."""
        return self._post("/config/batch", {"commands": commands})

    def factory_reset(self):
        """POST /config/factory_reset -- reset device to factory defaults."""
        return self._post("/config/factory_reset")

    # --- System actions ---

    def reboot(self):
        """POST /system/reboot -- reboot the device."""
        return self._post("/system/reboot")

    def get_system_ztp(self):
        """GET /system/ztp -- zero touch provisioning status and config."""
        return self._get("/system/ztp")
