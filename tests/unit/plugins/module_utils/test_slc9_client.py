from __future__ import absolute_import, division, print_function
__metaclass__ = type

import pytest
from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.module_utils.slc9_client import SLC9Client


def make_client():
    return SLC9Client(host="192.0.2.1", token="test-token-123", verify_ssl=False)


def test_build_url():
    client = make_client()
    assert client._url("/system/version") == "https://192.0.2.1/api/v2/system/version"


def test_get_system_version_returns_dict():
    client = make_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "model": "SLC9032",
        "current_firmware_version": "9.7.0.0R8",
        "sw_python_version": "3.13.2",
    }
    mock_response.raise_for_status = MagicMock()
    with patch.object(client.session, "get", return_value=mock_response) as mock_get:
        result = client.get_system_version()
        mock_get.assert_called_once_with("https://192.0.2.1/api/v2/system/version")
        assert result["model"] == "SLC9032"


def test_get_system_status_returns_dict():
    client = make_client()
    mock_response = MagicMock()
    mock_response.json.return_value = {"uptime": 34060479, "temperature": 58}
    mock_response.raise_for_status = MagicMock()
    with patch.object(client.session, "get", return_value=mock_response):
        result = client.get_system_status()
        assert result["uptime"] == 34060479


def test_get_raises_ansible_lantronix_error_on_http_error():
    from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError
    import requests as req
    client = make_client()
    err_resp = MagicMock()
    err_resp.status_code = 404
    err_resp.json.return_value = {"message": "not found"}
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = req.HTTPError(response=err_resp)
    with patch.object(client.session, "get", return_value=mock_response):
        with pytest.raises(AnsibleLantronixError, match="not found"):
            client.get_system_version()


def test_api_error_message_with_none_response():
    from ansible_collections.lantronix.oob.plugins.module_utils.common import api_error_message
    import requests as req
    exc = req.HTTPError("connection failed")
    exc.response = None
    result = api_error_message(exc)
    assert "connection failed" in result


def test_post_config_batch_connection_drop_verifies_success():
    """R21 drops the connection after applying commands that trigger a service
    restart. If the submitted commands show up in the running config afterward,
    treat it as success rather than raising."""
    import requests as req
    client = make_client()
    commands = ["set ntp state enable sync poll poll local localserver1 pool.ntp.org"]
    get_response = MagicMock()
    get_response.json.return_value = {"commands": commands}
    get_response.raise_for_status = MagicMock()
    with patch("time.sleep"), \
         patch.object(client.session, "post", side_effect=req.exceptions.ConnectionError()), \
         patch.object(client.session, "get", return_value=get_response):
        result = client.post_config_batch(commands)
        assert result["commands"] == commands


def test_post_config_batch_connection_drop_raises_when_not_confirmed():
    """If the connection drops and the submitted commands are NOT present in
    the running config afterward, this is a genuine failure -- raise rather
    than silently returning as if it succeeded."""
    from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError
    import requests as req
    client = make_client()
    commands = ["set ntp srcipaddr eth1"]
    get_response = MagicMock()
    get_response.json.return_value = {"commands": ["set hostname slc9k-dc1"]}
    get_response.raise_for_status = MagicMock()
    with patch("time.sleep"), \
         patch.object(client.session, "post", side_effect=req.exceptions.ReadTimeout()), \
         patch.object(client.session, "get", return_value=get_response):
        with pytest.raises(AnsibleLantronixError, match="set ntp srcipaddr eth1"):
            client.post_config_batch(commands)
