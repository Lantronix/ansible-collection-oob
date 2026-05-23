from __future__ import absolute_import, division, print_function
__metaclass__ = type

import hashlib
from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_config


def _hash(data):
    if not data:
        return ""
    return "sha256:" + hashlib.sha256(data.encode("utf-8")).hexdigest()


def _existing(data="set hostname x", content_type="config"):
    return {"result": [{"id": "c-001", "name": "baseline-config", "type": content_type, "description": _hash(data)}]}


NO_CONTENT = {"result": []}
# Fixture for an item created outside this module (no hash in description)
EXISTING_UNMANAGED = {"result": [{"id": "c-001", "name": "baseline-config", "type": "config", "description": "user description"}]}


def run_module(params, check_mode=False, search_result=None):
    result = search_result if search_result is not None else NO_CONTENT
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_config.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_config.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_config.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_content.return_value = result
                instance.create_content.return_value = {"id": "c-002"}
                instance.delete_content.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_csrf_token.return_value = "test-csrf"
                _conn_opts = {"host": "api.consoleflow.com", "validate_certs": False}
                mock_conn.get_option.side_effect = _conn_opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_config.main()
                return m, instance, mock_cls


def test_creates_when_missing():
    m, client, mock_cls = run_module({"name": "baseline-config", "content_type": "config", "data": "set hostname x", "state": "present"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_content.assert_called_once_with("baseline-config", "config", "set hostname x", description=_hash("set hostname x"))


def test_no_change_when_exists_same_data():
    m, client, mock_cls = run_module(
        {"name": "baseline-config", "content_type": "config", "data": "set hostname x", "state": "present"},
        search_result=_existing("set hostname x"),
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_content.assert_not_called()
    client.delete_content.assert_not_called()


def test_update_when_data_changes():
    m, client, mock_cls = run_module(
        {"name": "baseline-config", "content_type": "config", "data": "set hostname y", "state": "present"},
        search_result=_existing("set hostname x"),
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_content.assert_called_once_with("c-001")
    client.create_content.assert_called_once_with("baseline-config", "config", "set hostname y", description=_hash("set hostname y"))


def test_update_when_type_changes():
    m, client, mock_cls = run_module(
        {"name": "baseline-config", "content_type": "script", "data": "set hostname x", "state": "present"},
        search_result=_existing("set hostname x", content_type="config"),
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_content.assert_called_once_with("c-001")
    client.create_content.assert_called_once_with("baseline-config", "script", "set hostname x", description=_hash("set hostname x"))


def test_check_mode_blocks_update():
    m, client, mock_cls = run_module(
        {"name": "baseline-config", "content_type": "config", "data": "set hostname y", "state": "present"},
        check_mode=True,
        search_result=_existing("set hostname x"),
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_content.assert_not_called()
    client.create_content.assert_not_called()


def test_deletes_when_absent():
    m, client, mock_cls = run_module(
        {"name": "baseline-config", "content_type": "config", "data": None, "state": "absent"},
        search_result=_existing(),
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_content.assert_called_once_with("c-001")


def test_check_mode_blocks_create():
    m, client, mock_cls = run_module(
        {"name": "new-config", "content_type": "config", "data": "x", "state": "present"},
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_content.assert_not_called()


def test_unmanaged_item_no_false_positive():
    """Items without a hash in description (created outside this module) should not trigger updates."""
    m, client, mock_cls = run_module(
        {"name": "baseline-config", "content_type": "config", "data": "anything", "state": "present"},
        search_result=EXISTING_UNMANAGED,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_content.assert_not_called()
    client.delete_content.assert_not_called()


def test_percepxion_config_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"name": "cfg", "content_type": "config", "data": None, "state": "present"})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
