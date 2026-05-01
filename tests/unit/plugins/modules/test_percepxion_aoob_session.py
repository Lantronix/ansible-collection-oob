from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_aoob_session


def run_module(params, check_mode=False):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_aoob_session.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_aoob_session.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_aoob_session.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.initiate_session.return_value = {"session_id": "sess-abc123"}
                instance.terminate_session.return_value = {}
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

                percepxion_aoob_session.main()
                return m, instance, mock_cls


def test_initiates_session_for_device():
    m, client, mock_cls = run_module({"device_id": "dev-001", "session_id": None, "state": "present"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    assert kwargs["session_id"] == "sess-abc123"
    client.initiate_session.assert_called_once_with("dev-001")


def test_terminates_session():
    m, client, mock_cls = run_module({"device_id": None, "session_id": "sess-abc123", "state": "absent"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.terminate_session.assert_called_once_with("sess-abc123")


def test_check_mode_blocks_initiate():
    m, client, mock_cls = run_module({"device_id": "dev-001", "session_id": None, "state": "present"}, check_mode=True)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.initiate_session.assert_not_called()


def test_check_mode_blocks_terminate():
    m, client, mock_cls = run_module({"device_id": None, "session_id": "sess-abc123", "state": "absent"}, check_mode=True)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.terminate_session.assert_not_called()


def test_percepxion_aoob_session_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"device_id": "dev-001", "session_id": None, "state": "present"})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
