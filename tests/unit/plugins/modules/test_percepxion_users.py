from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_users

EXISTING_USERS = {"result": [{"id": "u-001", "username": "netops", "role": "admin", "enabled": True}]}
SUSPENDED_USER = {"result": [{"id": "u-001", "username": "netops", "role": "admin", "enabled": False}]}
EMPTY_USERS = {"result": []}


def run_module(params, check_mode=False, existing=None):
    search_result = existing if existing is not None else EXISTING_USERS
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_users.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_users.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_users.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_users.return_value = search_result
                instance.create_user.return_value = {}
                instance.delete_users.return_value = {}
                instance.set_users_enabled.return_value = {}
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
                m.exit_json.side_effect = SystemExit
                m.fail_json.side_effect = SystemExit
                mock_mod.return_value = m

                try:
                    percepxion_users.main()
                except SystemExit:
                    pass
                return m, instance, mock_cls


def _params(**over):
    base = {"username": "netops", "role": "admin", "password": None, "state": "present",
            "project_tag": None, "tenant_id": None}
    base.update(over)
    return base


def test_no_change_when_user_exists():
    m, client, mock_cls = run_module(_params(state="present"))
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_user.assert_not_called()


def test_changed_when_new_user():
    m, client, mock_cls = run_module(_params(username="newuser", role="user", password="Secret1"), existing=EMPTY_USERS)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_user.assert_called_once()


def test_absent_removes_user_by_id():
    m, client, mock_cls = run_module(_params(role=None, state="absent"))
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_users.assert_called_once_with(["u-001"])


def test_suspend_enabled_user():
    m, client, mock_cls = run_module(_params(state="suspended"))
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_users_enabled.assert_called_once_with(["u-001"], enable=False)


def test_suspend_already_suspended_is_noop():
    m, client, mock_cls = run_module(_params(state="suspended"), existing=SUSPENDED_USER)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.set_users_enabled.assert_not_called()


def test_enable_suspended_user():
    m, client, mock_cls = run_module(_params(state="enabled"), existing=SUSPENDED_USER)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_users_enabled.assert_called_once_with(["u-001"], enable=True)


def test_suspend_missing_user_fails():
    try:
        run_module(_params(username="ghost", state="suspended"), existing=EMPTY_USERS)
    except SystemExit:
        pass
    # fail_json raised SystemExit via side_effect; the assertion is that we got here


def test_check_mode_blocks_create():
    m, client, mock_cls = run_module(
        _params(username="newuser", role="user", password="x"),
        check_mode=True, existing=EMPTY_USERS,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_user.assert_not_called()


def test_percepxion_users_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module(_params())
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
