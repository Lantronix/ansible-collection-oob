from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
name: slc9
short_description: HttpApi plugin for Lantronix SLC 9000 REST API v2
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Manages authentication and request routing for SLC 9000 REST API v2.
  - Login posts credentials to POST /api/v2/user/login and stores the returned token.
options: {}
"""

import json
try:
    import requests as _requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    _requests = None  # type: ignore
from ansible.plugins.httpapi import HttpApiBase
from ansible.module_utils.connection import ConnectionError


class HttpApi(HttpApiBase):
    """HttpApi plugin for SLC 9000 REST API v2."""

    def login(self, username, password):
        # Use requests directly to avoid netcommon injecting Authorization: Basic
        # when _auth is None, which can interfere with token-based auth.
        if not HAS_REQUESTS:
            raise ConnectionError("The requests Python library is required for this plugin.")
        host = self.connection.get_option("host")
        verify = self.connection.get_option("validate_certs")
        url = "https://{0}/api/v2/user/login".format(host)
        try:
            resp = _requests.post(
                url,
                json={"username": username, "password": password},
                headers={"Content-Type": "application/json"},
                verify=verify,
                timeout=30,
            )
            resp.raise_for_status()
            body = resp.json()
        except Exception as exc:
            raise ConnectionError("SLC 9000 login failed: {0}".format(str(exc)))

        token = body.get("token")
        if not token:
            raise ConnectionError("SLC 9000 login failed: no token in response")

        self.connection._auth = {"X-auth-token": token}

    def logout(self):
        try:
            self.connection.send(
                "/api/v2/user/login",
                None,
                method="DELETE",
                headers=self.connection._auth or {},
            )
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
            raise ConnectionError("SLC 9000: authentication error (401). Check credentials.")
        if exc.code == 403:
            raise ConnectionError("SLC 9000: forbidden (403). User lacks rights for this endpoint.")
        if exc.code == 404:
            raise ConnectionError(
                "SLC 9000: endpoint not found (404). Verify firmware supports API v2 (requires R7+)."
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
                "SLC 9000: unexpected non-JSON response from {0}: {1}".format(path, raw_text[:200])
            )
