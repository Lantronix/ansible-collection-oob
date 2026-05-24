from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
name: slc9
short_description: HttpApi plugin for Lantronix SLC9000 REST API v2
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Manages authentication and request routing for SLC9000 REST API v2.
  - Login posts credentials to POST /api/v2/user/login and stores the returned token.
options: {}
"""

import json
import socket
import ssl
from ansible.plugins.httpapi import HttpApiBase
from ansible.module_utils.connection import ConnectionError


class HttpApi(HttpApiBase):
    """HttpApi plugin for SLC9000 REST API v2."""

    def login(self, username, password):
        # mini_httpd on SLC9000 cannot handle HTTP requests where headers and
        # body arrive in separate TCP writes. requests/http.client always split
        # them. We use raw sockets with a single sendall() to keep the full
        # request in one TLS record.
        host = self.connection.get_option("host")
        verify = self.connection.get_option("validate_certs")

        body_bytes = json.dumps(
            {"username": username, "password": password},
            separators=(",", ":"),
        ).encode("utf-8")

        request = (
            b"POST /api/v2/user/login HTTP/1.1\r\n"
            + ("Host: {0}\r\n".format(host)).encode()
            + b"Content-Type: application/json\r\n"
            + ("Content-Length: {0}\r\n".format(len(body_bytes))).encode()
            + b"Connection: close\r\n"
            + b"\r\n"
            + body_bytes
        )

        ctx = ssl.create_default_context()
        if not verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        try:
            raw_sock = socket.create_connection((host, 443), timeout=30)
            tls_sock = ctx.wrap_socket(raw_sock, server_hostname=host)
            tls_sock.sendall(request)
            response = b""
            while True:
                chunk = tls_sock.recv(4096)
                if not chunk:
                    break
                response += chunk
            tls_sock.close()
        except Exception as exc:
            raise ConnectionError("SLC9000 login failed: {0}".format(str(exc)))

        # Parse status line
        status_line = response.split(b"\r\n", 1)[0]
        try:
            status_code = int(status_line.split(b" ", 2)[1])
        except (IndexError, ValueError):
            raise ConnectionError("SLC9000 login failed: malformed HTTP response")

        header_end = response.find(b"\r\n\r\n")
        resp_body = response[header_end + 4:] if header_end != -1 else b""

        if status_code != 200:
            raise ConnectionError(
                "SLC9000 login failed: HTTP {0} from {1}".format(status_code, host)
            )

        try:
            parsed = json.loads(resp_body)
        except ValueError:
            raise ConnectionError("SLC9000 login failed: non-JSON response from {0}".format(host))

        token = parsed.get("token")
        if not token:
            raise ConnectionError("SLC9000 login failed: no token in response from {0}".format(host))

        self.connection._auth = {"X-auth-token": token}

    def logout(self):
        # Use raw socket (like login) so mini_httpd can handle the DELETE even
        # when the Ansible connection layer is already being torn down.
        auth = self.connection._auth or {}
        token = auth.get("X-auth-token")
        if token:
            host = self.connection.get_option("host")
            verify = self.connection.get_option("validate_certs")

            request = (
                b"DELETE /api/v2/user/login HTTP/1.1\r\n"
                + ("Host: {0}\r\n".format(host)).encode()
                + ("X-auth-token: {0}\r\n".format(token)).encode()
                + b"Content-Length: 0\r\n"
                + b"Connection: close\r\n"
                + b"\r\n"
            )

            ctx = ssl.create_default_context()
            if not verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            try:
                raw_sock = socket.create_connection((host, 443), timeout=10)
                tls_sock = ctx.wrap_socket(raw_sock, server_hostname=host)
                tls_sock.sendall(request)
                while True:
                    if not tls_sock.recv(4096):
                        break
                tls_sock.close()
            except Exception:
                pass

        self.connection._auth = None

    def get_token(self):
        if self.connection._auth is None:
            self.connection._connect()
        return (self.connection._auth or {}).get("X-auth-token")

    def handle_httperror(self, exc):
        if not hasattr(exc, "code"):
            return False
        if exc.code == 401:
            raise ConnectionError("SLC9000: authentication error (401). Check credentials.")
        if exc.code == 403:
            raise ConnectionError("SLC9000: forbidden (403). User lacks rights for this endpoint.")
        if exc.code == 404:
            raise ConnectionError(
                "SLC9000: endpoint not found (404). Verify firmware supports API v2 (requires R7+)."
            )
        return False

    def send_request(self, data, **message_kwargs):
        """Send an authenticated API request.

        ``data`` is the URL path (str), named ``data`` to match the
        HttpApiBase.send_request signature. Pass ``body``, ``method``, and
        ``headers`` as keyword arguments via ``message_kwargs``.
        """
        path = data
        method = message_kwargs.get("method", "GET")
        body = message_kwargs.get("body", None)
        extra_headers = message_kwargs.get("headers", None)

        req_headers = dict(self.connection._auth or {})
        req_headers["Content-Type"] = "application/json"
        if extra_headers:
            req_headers.update(extra_headers)

        response, response_data = self.connection.send(
            path, json.dumps(body) if body is not None else None, method=method, headers=req_headers
        )
        raw = response_data.read()
        try:
            return json.loads(raw)
        except Exception:
            raw_text = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else str(raw)
            raise ConnectionError(
                "SLC9000: unexpected non-JSON response from {0}: {1}".format(path, raw_text[:200])
            )
