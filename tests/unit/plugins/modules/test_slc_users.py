from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_users

EXISTING_USERS = {"users": [{"username": "netops", "role": "admin"}]}


def run_module(params, check_mode=False):
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_users.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_users.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_users.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_users.return_value = EXISTING_USERS
                instance.set_users.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_option.return_value = "192.0.2.1"
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_users.main()
                return m, instance


def test_present_user_already_exists_no_change():
    m, client = run_module({"username": "netops", "state": "present", "role": "admin", "password": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.set_users.assert_not_called()


def test_present_new_user_triggers_change():
    m, client = run_module({"username": "newuser", "state": "present", "role": "user", "password": "Secret123"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_users.assert_called_once()


def test_absent_existing_user_triggers_change():
    m, client = run_module({"username": "netops", "state": "absent", "role": None, "password": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True


def test_check_mode_does_not_call_set():
    m, client = run_module(
        {"username": "newuser", "state": "present", "role": "user", "password": "x"}, check_mode=True
    )
    client.set_users.assert_not_called()
