from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_system

MOCK_IDENTITY = {"hostname": "slc9k-lab", "description": "Lab console server"}


def run_module(params, check_mode=False, identity=None):
    current_identity = identity if identity is not None else MOCK_IDENTITY
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_system.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_system.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_system.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_system_identity.return_value = current_identity
                instance.set_system_identity.return_value = {}
                instance.reboot.return_value = {}
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

                slc_system.main()
                return m, instance, mock_cls


def test_no_change_when_hostname_matches():
    m, client, mock_cls = run_module({
        "hostname": "slc9k-lab",
        "description": None,
        "reboot": False,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.set_system_identity.assert_not_called()


def test_changed_when_hostname_differs():
    m, client, mock_cls = run_module({
        "hostname": "slc9k-prod",
        "description": None,
        "reboot": False,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_system_identity.assert_called_once()


def test_changed_when_description_differs():
    m, client, mock_cls = run_module({
        "hostname": None,
        "description": "Production console server",
        "reboot": False,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_system_identity.assert_called_once()


def test_reboot_always_changed():
    m, client, mock_cls = run_module({
        "hostname": None,
        "description": None,
        "reboot": True,
        "state": "present",
    })
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.reboot.assert_called_once()


def test_check_mode_blocks_identity_change():
    m, client, mock_cls = run_module(
        {
            "hostname": "new-hostname",
            "description": None,
            "reboot": False,
            "state": "present",
        },
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.set_system_identity.assert_not_called()


def test_check_mode_blocks_reboot():
    m, client, mock_cls = run_module(
        {
            "hostname": None,
            "description": None,
            "reboot": True,
            "state": "present",
        },
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.reboot.assert_not_called()


def test_slc_system_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"hostname": None, "description": None, "reboot": False})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
