from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_users

EXISTING_USERS = {"users": [{"username": "netops", "role": "admin"}]}
EMPTY_USERS = {"users": []}


def run_module(params, check_mode=False, existing=None):
    search_result = existing if existing is not None else EXISTING_USERS
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_users.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_users.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_users.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_users.return_value = search_result
                instance.create_user.return_value = {}
                instance.delete_user.return_value = {}
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

                percepxion_users.main()
                return m, instance, mock_cls


def test_no_change_when_user_exists():
    m, client, mock_cls = run_module({"username": "netops", "role": "admin", "password": None, "state": "present"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_user.assert_not_called()


def test_changed_when_new_user():
    m, client, mock_cls = run_module(
        {"username": "newuser", "role": "user", "password": "Secret1", "state": "present"},
        existing=EMPTY_USERS,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_user.assert_called_once()


def test_absent_removes_user():
    m, client, mock_cls = run_module({"username": "netops", "role": None, "password": None, "state": "absent"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_user.assert_called_once_with("netops")


def test_check_mode_blocks_create():
    m, client, mock_cls = run_module(
        {"username": "newuser", "role": "user", "password": "x", "state": "present"},
        check_mode=True,
        existing=EMPTY_USERS,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_user.assert_not_called()


def test_percepxion_users_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"username": "netops", "role": "admin", "password": None, "state": "present"})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
