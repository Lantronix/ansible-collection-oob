from __future__ import absolute_import, division, print_function
__metaclass__ = type

import json as _json
import socket as _socket
import ssl as _ssl
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
        self._token = token
        self.verify_ssl = verify_ssl
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "X-auth-token": token,
        })
        self.session.verify = verify_ssl

    def _url(self, path):
        return "https://{0}{1}{2}".format(self.host, self.BASE_PATH, path)

    def _raw_write(self, method, path, data=None, close_expected=False):
        """Send a write request via raw TLS socket using a single sendall().

        mini_httpd on SLC9000 cannot handle requests where headers and body
        arrive in separate TCP writes (which requests always does for bodies).
        This method sends the complete request, headers + body, in one TLS
        record, which mini_httpd can parse correctly.

        Set close_expected=True for endpoints that close the TCP connection
        without sending an HTTP response (config/batch, system/identity, etc.).
        """
        body_bytes = (_json.dumps(data, separators=(",", ":")).encode("utf-8")
                      if data is not None else b"")
        full_path = "{0}{1}".format(self.BASE_PATH, path)

        request = (
            "{0} {1} HTTP/1.1\r\n".format(method, full_path).encode()
            + "Host: {0}\r\n".format(self.host).encode()
            + "X-auth-token: {0}\r\n".format(self._token).encode()
            + b"Content-Type: application/json\r\n"
            + "Content-Length: {0}\r\n".format(len(body_bytes)).encode()
            + b"Connection: close\r\n"
            + b"\r\n"
            + body_bytes
        )

        ctx = _ssl.create_default_context()
        if not self.verify_ssl:
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE

        try:
            raw_sock = _socket.create_connection((self.host, 443), timeout=30)
            tls_sock = ctx.wrap_socket(raw_sock, server_hostname=self.host)
            tls_sock.sendall(request)
            response = b""
            while True:
                chunk = tls_sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            tls_sock.close()
        except Exception as exc:
            if close_expected:
                return {}
            raise AnsibleLantronixError(
                "SLC9000: connection error on {0} {1}: {2}".format(method, path, exc)
            )

        if not response:
            if close_expected:
                return {}
            raise AnsibleLantronixError(
                "SLC9000: no response from {0} {1}".format(method, path)
            )

        status_line = response.split(b"\r\n", 1)[0]
        try:
            status_code = int(status_line.split(b" ", 2)[1])
        except (IndexError, ValueError):
            raise AnsibleLantronixError(
                "SLC9000: malformed HTTP response from {0} {1}".format(method, path)
            )

        header_end = response.find(b"\r\n\r\n")
        resp_body = response[header_end + 4:] if header_end != -1 else b""

        if status_code >= 400:
            try:
                error_body = _json.loads(resp_body)
                msg = error_body.get("message") or error_body.get("error") or str(status_code)
                if isinstance(msg, list):
                    msg = "; ".join(str(m) for m in msg)
            except Exception:
                msg = "HTTP {0} from {1} {2}".format(status_code, method, path)
            raise AnsibleLantronixError(msg)

        if not resp_body.strip():
            return {}
        try:
            return _json.loads(resp_body)
        except ValueError:
            raise AnsibleLantronixError(
                "SLC9000: non-JSON response from {0} {1}: {2!r}".format(
                    method, path, resp_body[:200]
                )
            )

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
        return self._raw_write("POST", path, data)

    def _put(self, path, data=None):
        return self._raw_write("PUT", path, data)

    def _patch(self, path, data=None):
        return self._raw_write("PATCH", path, data)

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
        """PUT /network/interfaces -- update interface config.

        The device restarts the network subsystem after applying interface changes,
        closing the TCP connection before sending an HTTP response.
        """
        try:
            resp = self.session.put(self._url("/network/interfaces"), json=payload, timeout=30)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            time.sleep(3)
            return self.get_network_interfaces()

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
        """GET /firmware/update_status -- ongoing update progress.

        Returns a plain-text log (not JSON) while an update is in progress.
        Falls back to a structured dict with status=in_progress in that case.
        """
        try:
            resp = self.session.get(self._url("/firmware/update_status"))
            resp.raise_for_status()
            try:
                return resp.json()
            except ValueError:
                return {"status": "in_progress", "progress": 0, "message": resp.text}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

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
        """POST /config/batch -- execute a list of CLI config commands.

        The device closes the TCP connection after applying commands without
        sending an HTTP response. Catch ConnectionError and treat it as success,
        then verify via a lightweight GET to confirm the device is still reachable.
        """
        try:
            resp = self.session.post(self._url("/config/batch"), json={"commands": commands}, timeout=30)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            time.sleep(2)
            return self.get_system_version()

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
