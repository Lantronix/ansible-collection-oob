from __future__ import absolute_import, division, print_function
__metaclass__ = type

import io
import json as _json

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

from ansible_collections.lantronix.oob.plugins.module_utils.common import api_error_message, AnsibleLantronixError


class PercepxionClient:
    """REST client for Percepxion API (6.12, OpenAPI 3.0.1).

    Auth uses two tokens returned from POST /v2/user/login:
      - token       -> x-mystq-token header (all requests)
      - csrf_token  -> x-csrf-token header (all requests; server ignores on GETs)

    project_tag and tenant_id scope device operations to a project.
    Pass tenant_id only when authenticating as a Project Admin.
    """

    def __init__(self, host, token, csrf_token, project_tag=None, tenant_id=None, verify_ssl=True):
        self.host = host
        self.project_tag = project_tag
        self.tenant_id = tenant_id
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "x-mystq-token": token,
            "x-csrf-token": csrf_token,
        })
        self.session.verify = verify_ssl

    def _url(self, path):
        return "https://{0}/api{1}".format(self.host, path)

    def _scope(self, extra=None):
        """Build a base payload with optional project/tenant scoping."""
        payload = {}
        if self.project_tag:
            payload["project_tag"] = self.project_tag
        if self.tenant_id:
            payload["tenant_id"] = self.tenant_id
        if extra:
            payload.update(extra)
        return payload

    def _get(self, path):
        try:
            resp = self.session.get(self._url(path))
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

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

    def _delete(self, path, data=None):
        try:
            kwargs = {"json": data} if data is not None else {}
            resp = self.session.delete(self._url(path), **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

    # --- Devices ---

    def search_devices(self, search_string=None, limit=100, offset=0):
        payload = self._scope()
        if search_string:
            payload["search_string"] = search_string
        payload["limit"] = limit
        payload["offset"] = offset
        return self._post("/v3/device/search", payload)

    def get_device(self, device_id):
        # API expects device_id as an array; returns {"total": N, "result": [...]}
        resp = self._post("/v3/device/get", self._scope({"device_id": [device_id]}))
        results = resp.get("result", [])
        return results[0] if results else {}

    def update_device(self, device_id, updates):
        return self._post("/v3/device/update", self._scope(dict(device_id=device_id, **updates)))

    def assign_device(self, device_id, project_tag=None):
        return self._post("/v3/device/assign", self._scope({
            "device_id": device_id,
            "project_tag": project_tag or self.project_tag,
        }))

    def unassign_device(self, device_id):
        # API expects device_id as an array
        return self._post("/v3/device/unassign", self._scope({"device_id": [device_id]}))

    # --- Smart Groups ---

    def create_smart_group(self, name, query_string=None, device_ids=None):
        payload = self._scope({"name": name})
        if query_string:
            payload["query_string"] = query_string
        elif device_ids:
            payload["device_ids"] = device_ids
        return self._post("/v3/device/smartgroup/create", payload)

    def search_smart_groups(self, search_string=None, limit=100):
        payload = self._scope({"limit": limit})
        if search_string:
            payload["search_string"] = search_string
        return self._post("/v3/device/smartgroup/search", payload)

    def delete_smart_group(self, group_id):
        return self._post("/v3/device/smartgroup/delete", self._scope({"id": [group_id]}))

    # --- Content (config files) ---

    def create_content(self, name, content_type, data, version="1.0", description=""):
        """Upload a content file using multipart/form-data (required by the API).

        The session Content-Type header is excluded so requests can set the
        multipart boundary correctly.
        """
        metadata = _json.dumps(self._scope({
            "name": name,
            "type": content_type,
            "version": version,
            "opcode": "download",
            "description": description,
        }))
        files = {
            "file": (name + ".cfg", io.BytesIO(data.encode("utf-8")), "text/plain"),
            "data": (None, metadata, "application/json"),
        }
        headers = {k: v for k, v in self.session.headers.items()
                   if k.lower() != "content-type"}
        try:
            resp = requests.post(
                self._url("/v3/content/create"),
                files=files,
                headers=headers,
                verify=self.session.verify,
            )
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

    def search_content(self, content_type=None, limit=100):
        payload = self._scope({"limit": limit})
        if content_type:
            payload["type"] = content_type
        return self._post("/v3/content/search", payload)

    def update_content(self, content_id, updates):
        return self._post("/v3/content/update", self._scope(dict(content_id=content_id, **updates)))

    def delete_content(self, content_id):
        return self._post("/v3/content/delete", self._scope({"id": [content_id]}))

    # --- Jobs ---

    def create_job_group(self, payload):
        return self._post("/v1/job/jobgroup/create", self._scope(payload))

    def search_job_groups(self, search_string=None, limit=100):
        payload = self._scope({"limit": limit})
        if search_string:
            payload["search_string"] = search_string
        return self._post("/v1/job/jobgroup/search", payload)

    def delete_job_group(self, job_group_id):
        return self._post("/v1/job/jobgroup/delete", self._scope({"job_group_id": job_group_id}))

    def enable_job_groups(self, job_group_ids, enabled=True):
        return self._put("/v1/job/jobgroup/enable", self._scope({
            "job_group_ids": job_group_ids,
            "enabled": enabled,
        }))

    def search_job_logs(self, job_group_id=None, limit=100):
        payload = self._scope({"limit": limit})
        if job_group_id:
            payload["job_group_id"] = job_group_id
        return self._post("/v1/job/log/search", payload)

    def notify_job(self, payload):
        return self._post("/v1/job/notify", self._scope(payload))

    # --- Audit Logs ---

    def search_audit_logs(self, start_time=None, end_time=None, limit=100):
        payload = self._scope({"limit": limit})
        if start_time:
            payload["start_time"] = start_time
        if end_time:
            payload["end_time"] = end_time
        return self._post("/v1/audit/search", payload)

    def search_user_audit_logs(self, limit=100):
        return self._post("/v1/audit/user/search", self._scope({"limit": limit}))

    def download_device_log(self, device_id, log_level="info"):
        """POST /v1/storage/file/devicelog/download -- returns raw log text (text/plain)."""
        try:
            resp = self.session.post(self._url("/v1/storage/file/devicelog/download"),
                                     json=self._scope({"device_id": device_id, "log_level": log_level}))
            resp.raise_for_status()
            return resp.text
        except requests.HTTPError as exc:
            raise AnsibleLantronixError(api_error_message(exc))

    # --- Telemetry ---

    def get_telemetry_stats(self, device_id, metrics):
        return self._post("/v1/telemetry/stat/view", self._scope({
            "device_id": device_id,
            "metrics": metrics,
        }))

    def get_telemetry_history(self, device_id, metric, start_time, end_time):
        return self._post("/v1/storage/telemetry/history", self._scope({
            "device_id": [device_id],
            "name": metric,
            "from_date": start_time,
            "to_date": end_time,
        }))

    # --- Users ---

    def search_users(self, search_string=None, limit=1000, offset=0, sort="username", order="asc"):
        # /v2/user/search requires offset/limit/sort/order (6.13); response is
        # {total, result:[{id, username, ..., enabled}]}.
        payload = self._scope({
            "offset": offset,
            "limit": limit,
            "sort": sort,
            "order": order,
        })
        if search_string:
            payload["search_string"] = search_string
        return self._post("/v2/user/search", payload)

    def create_user(self, username, role, password=None):
        payload = self._scope({"username": username, "role": role})
        if password:
            payload["password"] = password
        return self._post("/v2/user/create", payload)

    def set_users_enabled(self, user_ids, enable):
        """PUT /v1/user, bulk suspend (enable=False) or resume (enable=True).

        Verified live 2026-08-27. Body is {users:[{user_id, enable}]}; tenant_id
        is added by _scope for project_admin.
        """
        users = [{"user_id": uid, "enable": bool(enable)} for uid in user_ids]
        return self._put("/v1/user", self._scope({"users": users}))

    def delete_users(self, user_ids):
        """DELETE /v1/user, bulk delete by id. Body is {users:[{id}]}."""
        users = [{"id": uid} for uid in user_ids]
        return self._delete("/v1/user", self._scope({"users": users}))

    # --- Device registration ---

    def register_device(self, payload):
        """POST /v1/device/register, register a new device by serial/MAC."""
        return self._post("/v1/device/register", self._scope(payload))

    # --- AOOB sessions (endpoint paths TBD, confirm with Percepxion backend team against production API) ---

    def initiate_session(self, device_id):
        """POST /v3/device/connect, initiate an OOB terminal session."""
        return self._post("/v3/device/connect", self._scope({"device_id": device_id}))

    def terminate_session(self, session_id):
        """POST /v3/device/disconnect, terminate an active OOB session."""
        return self._post("/v3/device/disconnect", self._scope({"session_id": session_id}))

    # --- Event rules & actions (all shapes verified live 2026-08-27) ---

    def search_event_rules(self, limit=100, offset=0):
        # Response: {total_results, rules:[{id, name, enable, device_ids, conditions, ...}]}
        return self._post("/v1/event/rule/search", self._scope({"offset": offset, "limit": limit}))

    def create_event_rule(self, name, conditions, enable=True, device_id=None,
                          smart_group_id=None, device_search=None, app_code=None):
        """POST /v1/event/rule/create. Target ONE of device_id (device_keys),
        smart_group_id, or device_search='*'. Returns {status, code, message[]}
        with no id; re-query rule/search for the id.
        """
        payload = self._scope({"name": name, "conditions": conditions, "enable": enable})
        if device_id:
            payload["device_id"] = device_id
        if smart_group_id:
            payload["smart_group_id"] = smart_group_id
        if device_search:
            payload["device_search"] = device_search
        if app_code:
            payload["app_code"] = app_code
        return self._post("/v1/event/rule/create", payload)

    def update_event_rule(self, rule_id, name, conditions=None, enable=None,
                          device_id=None, smart_group_id=None, app_code=None):
        """PUT /v1/event/rule/update. A rule bound to a group cannot be re-scoped
        to individual devices or another group (400 VALIDATION_ERROR).
        """
        payload = self._scope({"id": rule_id, "name": name})
        if conditions is not None:
            payload["conditions"] = conditions
        if enable is not None:
            payload["enable"] = enable
        if device_id:
            payload["device_id"] = device_id
        if smart_group_id:
            payload["smart_group_id"] = smart_group_id
        if app_code:
            payload["app_code"] = app_code
        return self._put("/v1/event/rule/update", payload)

    def delete_event_rule(self, name):
        """POST /v1/event/rule/delete. Deletes by rule NAME, not id."""
        return self._post("/v1/event/rule/delete", self._scope({"name": name}))

    def get_rule_actions(self, rule_name):
        return self._post("/v1/event/action/get", self._scope({"rule_name": rule_name}))

    def create_rule_action(self, rule_name, details, name=None, description=None):
        """POST /v1/event/action/create. details is a list of
        {action_type: email|sms, action: <target>, enable, reminder_interval}.
        """
        payload = self._scope({"rule_name": rule_name, "details": details})
        if name:
            payload["name"] = name
        if description:
            payload["description"] = description
        return self._post("/v1/event/action/create", payload)

    def delete_rule_action(self, app_code, rule_name):
        """POST /v1/event/action/delete, by app_code + rule_name."""
        return self._post("/v1/event/action/delete", self._scope({
            "app_code": app_code, "rule_name": rule_name,
        }))

    def update_idle_connection(self, enable, timeout=None, consecutive_periods=None,
                               reminder_interval=None, app_code=None):
        """PUT /v1/event/idleconn/update (POST returns 405). One config per tenant."""
        payload = self._scope({"enable": enable})
        for key, val in (("timeout", timeout), ("consecutive_periods", consecutive_periods),
                         ("reminder_interval", reminder_interval), ("app_code", app_code)):
            if val is not None:
                payload[key] = val
        return self._put("/v1/event/idleconn/update", payload)

    # --- Device tags (shapes verified live 2026-08-27) ---

    def list_device_tags(self):
        """POST /v3/device/tag/view, returns {tag:[{id, name, color, background_color}]}."""
        return self._post("/v3/device/tag/view", self._scope())

    def create_device_tag(self, name, color, background_color):
        """POST /v3/device/tag/create. color and background_color are required HEX."""
        return self._post("/v3/device/tag/create", self._scope({
            "name": name, "color": color, "background_color": background_color,
        }))

    def delete_device_tag(self, tag_ids):
        """POST /v3/device/tag/delete. tag_ids is a list."""
        return self._post("/v3/device/tag/delete", self._scope({"id": tag_ids}))

    def assign_device_tag(self, tag_ids, device_ids):
        """POST /v3/device/tag/assign. {id:[tag_ids], device_id:[device_keys]}."""
        return self._post("/v3/device/tag/assign", self._scope({
            "id": tag_ids, "device_id": device_ids,
        }))

    def unassign_device_tag(self, tag_ids, device_ids):
        """POST /v3/device/tag/unassign. Same shape as assign."""
        return self._post("/v3/device/tag/unassign", self._scope({
            "id": tag_ids, "device_id": device_ids,
        }))
