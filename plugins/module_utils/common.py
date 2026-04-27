from __future__ import absolute_import, division, print_function
__metaclass__ = type


class AnsibleLantronixError(Exception):
    """Base exception for lantronix.oob module errors."""
    pass


def build_result(changed=False, data=None, diff=None):
    """Return a standardised result dict for module.exit_json()."""
    result = {"changed": changed}
    if data is not None:
        result.update(data)
    if diff is not None:
        result["diff"] = diff
    return result


def api_error_message(exc):
    """Extract a human-readable message from a requests.HTTPError."""
    try:
        body = exc.response.json()
        return body.get("message") or body.get("error") or str(exc)
    except Exception:
        return str(exc)
