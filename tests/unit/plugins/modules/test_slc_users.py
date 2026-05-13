from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_users

SYSADMIN_ATTRS = {
    "uid": "0",
    "username": "sysadmin",
    "group": "Administrators",
    "permissions": "ad,nt,sv",
    "data_ports": "1-32",
    "listen_ports": "1-32",
    "clear_ports": "1-32",
    "power_outlets": "1-8",
    "escape_seq": "\\x1bA",
    "break_seq": "\\x1bB",
    "allow_dialback": "n",
    "dialback_number": "",
    "status": "Active",
}


def run_module(params, check_mode=False, get_sysadmin_side_effect=None):
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_users.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_users.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_users.SLC9Client") as mock_cls:
                instance = MagicMock()
                if get_sysadmin_side_effect is not None:
                    instance.get_sysadmin.side_effect = get_sysadmin_side_effect
                else:
                    instance.get_sysadmin.return_value = SYSADMIN_ATTRS
                instance.set_sysadmin_password.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                _conn_opts = {"host": "192.0.2.1", "validate_certs": False}
                mock_conn.get_option.side_effect = _conn_opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_users.main()
                return m, instance, mock_cls


def test_read_only_no_change():
    m, client, _mock_cls = run_module({"new_password": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert kwargs["sysadmin"]["username"] == "sysadmin"
    client.set_sysadmin_password.assert_not_called()


def test_password_change_reports_changed():
    m, client, _mock_cls = run_module({"new_password": "NewPass123!"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_sysadmin_password.assert_called_once_with("NewPass123!")


def test_check_mode_does_not_call_patch():
    m, client, _mock_cls = run_module({"new_password": "NewPass123!"}, check_mode=True)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_sysadmin_password.assert_not_called()


def test_returns_sysadmin_dict():
    m, _client, _mock_cls = run_module({"new_password": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["sysadmin"] == SYSADMIN_ATTRS


def test_passes_verify_ssl_to_client():
    _m, _instance, mock_cls = run_module({"new_password": None})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
