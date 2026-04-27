from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.module_utils.percepxion_client import PercepxionClient


def make_client():
    return PercepxionClient(
        host="api.consoleflow.com",
        token="test-user-token",
        csrf_token="test-csrf",
        project_tag="test-project",
        verify_ssl=False,
    )


def test_auth_headers_set():
    client = make_client()
    assert client.session.headers["x-mystq-token"] == "test-user-token"
    assert client.session.headers["x-csrf-token"] == "test-csrf"


def test_search_devices_injects_project_tag():
    client = make_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {"total_results": 1, "search_results": [{"device_id": "abc"}]}
    mock_response.raise_for_status = MagicMock()
    with patch.object(client.session, "post", return_value=mock_response) as mock_post:
        result = client.search_devices()
        call_json = mock_post.call_args[1]["json"]
        assert call_json["project_tag"] == "test-project"
        assert result["total_results"] == 1


def test_search_devices_without_project_tag():
    client = PercepxionClient(
        host="api.consoleflow.com", token="t", csrf_token="c", verify_ssl=False
    )
    mock_response = MagicMock()
    mock_response.json.return_value = {"total_results": 0, "search_results": []}
    mock_response.raise_for_status = MagicMock()
    with patch.object(client.session, "post", return_value=mock_response) as mock_post:
        client.search_devices()
        call_json = mock_post.call_args[1]["json"]
        assert "project_tag" not in call_json


def test_post_raises_ansible_lantronix_error_on_http_error():
    from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError
    import requests as req
    client = make_client()
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = req.HTTPError(response=MagicMock(json=MagicMock(return_value={"error": "forbidden"})))
    with patch.object(client.session, "post", return_value=mock_response):
        with pytest.raises(AnsibleLantronixError, match="forbidden"):
            client.search_devices()
