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
