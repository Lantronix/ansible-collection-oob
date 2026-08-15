from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import slc_config
from ansible_collections.lantronix.oob.plugins.module_utils.common import AnsibleLantronixError

MOCK_COMMANDS = {"commands": ["set hostname slc9k-lab", "set ntp server 10.0.0.1"]}
MOCK_COMPARE = {"diff": "- set hostname old\n+ set hostname slc9k-lab"}
MOCK_BATCH_RESULT = {"status": 200, "code": "SUCCESS", "message": ["Configuration updated successfully."]}


def run_module(params, check_mode=False):
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_config.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_config.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_config.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.get_config_commands.return_value = MOCK_COMMANDS
                instance.compare_config.return_value = MOCK_COMPARE
                instance.save_config.return_value = {}
                instance.post_config_batch.return_value = MOCK_BATCH_RESULT
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

                slc_config.main()
                return m, instance, mock_cls


def test_get_returns_commands_unchanged():
    m, client, mock_cls = run_module({"action": "get", "commands": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert kwargs["commands"] == MOCK_COMMANDS["commands"]
    client.save_config.assert_not_called()
    client.post_config_batch.assert_not_called()


def test_compare_returns_diff_unchanged():
    m, client, mock_cls = run_module({"action": "compare", "commands": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert "diff" in kwargs
    client.save_config.assert_not_called()


def test_save_is_always_changed():
    m, client, mock_cls = run_module({"action": "save", "commands": None})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.save_config.assert_called_once()


def test_batch_calls_post_with_correct_commands():
    cmds = ["set hostname slc9k-prod", "set ntp server 10.1.1.1"]
    m, client, mock_cls = run_module({"action": "batch", "commands": cmds})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.post_config_batch.assert_called_once_with(cmds)


def test_batch_surfaces_api_response_as_result():
    """The batch action must not discard the API response -- command output
    (e.g. from show commands) needs to reach the playbook."""
    cmds = ["show ntp status"]
    m, client, mock_cls = run_module({"action": "batch", "commands": cmds})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["result"] == MOCK_BATCH_RESULT
    assert kwargs["result"]["message"] == ["Configuration updated successfully."]


def test_check_mode_blocks_save():
    m, client, mock_cls = run_module({"action": "save", "commands": None}, check_mode=True)
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.save_config.assert_not_called()


def test_check_mode_blocks_batch():
    m, client, mock_cls = run_module(
        {"action": "batch", "commands": ["set hostname x"]}, check_mode=True
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    assert "result" not in kwargs
    client.post_config_batch.assert_not_called()


def test_batch_fails_when_post_config_batch_cannot_confirm_success():
    """post_config_batch raises AnsibleLantronixError when a connection drop
    can't be confirmed as a real success -- slc_config must fail the task,
    not report changed=True regardless."""
    with patch("ansible_collections.lantronix.oob.plugins.modules.slc_config.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.slc_config.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.slc_config.SLC9Client") as mock_cls:
                instance = MagicMock()
                instance.post_config_batch.side_effect = AnsibleLantronixError(
                    "Connection dropped while applying batch commands and the following "
                    "could not be confirmed in the running configuration: set ntp srcipaddr eth1."
                )
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                _conn_opts = {"host": "192.0.2.1", "validate_certs": False}
                mock_conn.get_option.side_effect = _conn_opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = {"action": "batch", "commands": ["set ntp srcipaddr eth1"]}
                m.check_mode = False
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                slc_config.main()

                m.fail_json.assert_called_once()
                assert "could not be confirmed" in m.fail_json.call_args[1]["msg"]


def test_slc_config_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"action": "get", "commands": None})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
