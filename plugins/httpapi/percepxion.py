from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r"""
name: percepxion
short_description: HttpApi plugin for Percepxion REST API (6.12+)
version_added: "1.0.0"
author:
  - Lantronix Product Team (@lantronix)
description:
  - Manages authentication for Percepxion API.
  - Login posts to POST /v2/user/login and stores both x-mystq-token and x-csrf-token.
  - The CSRF token is injected on all requests; the server ignores it on GETs.
options:
  percepxion_project_tag:
    description: Project tag to scope all device operations. Set in inventory.
    type: str
    required: false
  percepxion_tenant_id:
    description: Tenant ID for Project Admin multi-tenant operations. Set in inventory.
    type: str
    required: false
"""

import json
from ansible.plugins.httpapi import HttpApiBase
from ansible.module_utils.connection import ConnectionError


class HttpApi(HttpApiBase):
    """HttpApi plugin for Percepxion REST API (OpenAPI 3.0.1, v6.12+)."""

    def login(self, username, password):
        data = json.dumps({"username": username, "password": password})
        try:
            response, response_data = self.connection.send(
                "/v2/user/login",
                data,
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            body = json.loads(response_data.read())
        except ConnectionError:
            raise
        except Exception as exc:
            raise ConnectionError("Percepxion login failed: {0}".format(str(exc)))

        token = body.get("token")
        csrf_token = body.get("csrf_token")
        if not token:
            raise ConnectionError("Percepxion login failed: no token in response")

        self.connection._auth = {
            "x-mystq-token": token,
            "x-csrf-token": csrf_token or "",
        }

    def logout(self):
        # Percepxion 6.12 has no logout endpoint; clear local auth state only.
        self.connection._auth = None

    def get_token(self):
        return (self.connection._auth or {}).get("x-mystq-token")

    def get_csrf_token(self):
        return (self.connection._auth or {}).get("x-csrf-token")

    def handle_httperror(self, exc):
        if not hasattr(exc, "code"):
            return False
        if exc.code == 401:
            raise ConnectionError("Percepxion: authentication error (401). Check credentials.")
        if exc.code == 403:
            raise ConnectionError(
                "Percepxion: forbidden (403). Check that the user has the required role, "
                "or re-authenticate if the session has expired."
            )
        if exc.code == 404:
            raise ConnectionError(
                "Percepxion: endpoint not found (404). Verify Percepxion version is 6.12+."
            )
        return False

    def send_request(self, data, **message_kwargs):
        """Send an authenticated API request.

        ``data`` is the URL path (str) — named ``data`` to match HttpApiBase.send_request
        signature and avoid a pylint arguments-renamed violation. Pass ``body``, ``method``,
        and ``headers`` as keyword arguments via ``message_kwargs``.
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
                "Percepxion: unexpected non-JSON response from {0}: {1}".format(path, raw_text[:200])
            )
