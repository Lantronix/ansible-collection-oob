from __future__ import absolute_import, division, print_function
__metaclass__ = type

import requests
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
        return "https://{0}{1}".format(self.host, path)

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
        return self._post("/v3/device/get", self._scope({"device_id": device_id}))

    def update_device(self, device_id, updates):
        return self._post("/v3/device/update", self._scope(dict(device_id=device_id, **updates)))

    def assign_device(self, device_id, project_tag=None):
        return self._post("/v3/device/assign", self._scope({
            "device_id": device_id,
            "project_tag": project_tag or self.project_tag,
        }))

    def unassign_device(self, device_id):
        return self._post("/v3/device/unassign", self._scope({"device_id": device_id}))

    # --- Smart Groups ---

    def create_smart_group(self, name, criteria):
        return self._post("/v3/device/smartgroup/create", self._scope({"name": name, "criteria": criteria}))

    def search_smart_groups(self, search_string=None):
        return self._post("/v3/device/smartgroup/search", self._scope(
            {"search_string": search_string} if search_string else {}
        ))

    def delete_smart_group(self, group_id):
        return self._post("/v3/device/smartgroup/delete", self._scope({"group_id": group_id}))

    # --- Content (config files) ---

    def create_content(self, name, content_type, data):
        return self._post("/v3/content/create", self._scope({"name": name, "type": content_type, "data": data}))

    def search_content(self, content_type=None):
        payload = self._scope()
        if content_type:
            payload["type"] = content_type
        return self._post("/v3/content/search", payload)

    def update_content(self, content_id, updates):
        return self._post("/v3/content/update", self._scope(dict(content_id=content_id, **updates)))

    def delete_content(self, content_id):
        return self._post("/v3/content/delete", self._scope({"content_id": content_id}))

    # --- Jobs ---

    def create_job_group(self, payload):
        return self._post("/v1/job/jobgroup/create", self._scope(payload))

    def search_job_groups(self, search_string=None):
        return self._post("/v1/job/jobgroup/search", self._scope(
            {"search_string": search_string} if search_string else {}
        ))

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

    def download_device_log(self, device_id, log_type="access"):
        return self._post("/v1/storage/file/devicelog/download", self._scope({
            "device_id": device_id,
            "log_type": log_type,
        }))

    # --- Telemetry ---

    def get_telemetry_stats(self, device_id, metrics):
        return self._post("/v1/telemetry/stat/view", self._scope({
            "device_id": device_id,
            "metrics": metrics,
        }))

    def get_telemetry_history(self, device_id, metric, start_time, end_time):
        return self._post("/v1/storage/telemetry/history", self._scope({
            "device_id": device_id,
            "metric": metric,
            "start_time": start_time,
            "end_time": end_time,
        }))
