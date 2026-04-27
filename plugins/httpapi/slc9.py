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
from ansible.plugins.httpapi import HttpApiBase
from ansible.module_utils.connection import ConnectionError


class HttpApi(HttpApiBase):
    """HttpApi plugin for SLC 9000 REST API v2."""

    def login(self, username, password):
        data = json.dumps({"username": username, "password": password})
        response, response_data = self.connection.send(
            "/api/v2/user/login",
            data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            body = json.loads(response_data.read())
        except Exception:
            raise ConnectionError("Failed to parse SLC 9000 login response")

        token = body.get("token")
        if not token:
            raise ConnectionError("SLC 9000 login failed: no token in response")

        self.connection._auth = {"x-user-token": token}

    def logout(self):
        self.connection.send(
            "/api/v2/user/login",
            None,
            method="DELETE",
            headers=self.connection._auth or {},
        )
        self.connection._auth = {}

    def get_token(self):
        return (self.connection._auth or {}).get("x-user-token")

    def handle_httperror(self, exc):
        if exc.code == 401:
            raise ConnectionError("SLC 9000: authentication error (401). Check credentials.")
        if exc.code == 403:
            raise ConnectionError("SLC 9000: forbidden (403). User lacks rights for this endpoint.")
        return False

    def send_request(self, data, **message_kwargs):
        """Send an authenticated API request.

        ``data`` is the URL path (str). Pass ``body``, ``method``, and
        ``headers`` as keyword arguments via ``message_kwargs`` so this
        override stays compatible with HttpApiBase.send_request.
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
            path, json.dumps(body) if body else None, method=method, headers=req_headers
        )
        try:
            return json.loads(response_data.read())
        except Exception:
            return {}
