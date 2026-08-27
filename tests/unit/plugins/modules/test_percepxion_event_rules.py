from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_event_rules

RULE = {"id": "r-001", "name": "dp-1_disconnected", "enable": True}


def run_module(params, check_mode=False, search_returns=None):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_event_rules.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_event_rules.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_event_rules.PercepxionClient") as mock_cls:
                instance = MagicMock()
                if search_returns is not None:
                    instance.search_event_rules.side_effect = search_returns
                else:
                    instance.search_event_rules.return_value = {"rules": []}
                instance.create_event_rule.return_value = {"status": "success"}
                instance.update_event_rule.return_value = {}
                instance.delete_event_rule.return_value = {}
                instance.create_rule_action.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "t"
                mock_conn.get_csrf_token.return_value = "c"
                _opts = {"host": "api.consoleflow.com", "validate_certs": False}
                mock_conn.get_option.side_effect = _opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                m.exit_json.side_effect = SystemExit
                m.fail_json.side_effect = SystemExit
                mock_mod.return_value = m

                try:
                    percepxion_event_rules.main()
                except SystemExit:
                    pass
                return m, instance


def _params(**over):
    base = {"name": "dp-1_disconnected", "state": "present", "enable": True,
            "conditions": [{"attr_path": "/x", "operator": "changed_with_val"}],
            "device_id": ["dev-1"], "smart_group_id": None, "device_search": None,
            "app_code": None, "actions": None, "project_tag": None, "tenant_id": None}
    base.update(over)
    return base


def test_create_when_missing():
    # first search (find) empty, second search (post-create id lookup) has the rule
    m, client = run_module(_params(), search_returns=[{"rules": []}, {"rules": [RULE]}])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_event_rule.assert_called_once()
    assert kwargs.get("rule_id") == "r-001"


def test_create_with_actions():
    m, client = run_module(
        _params(actions=[{"action_type": "email", "action": "a@b.com", "enable": True, "reminder_interval": 0}]),
        search_returns=[{"rules": []}, {"rules": [RULE]}],
    )
    assert m.exit_json.call_args[1]["changed"] is True
    client.create_rule_action.assert_called_once()


def test_no_change_when_enable_matches():
    m, client = run_module(_params(enable=True), search_returns=[{"rules": [RULE]}])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_event_rule.assert_not_called()
    client.update_event_rule.assert_not_called()


def test_update_when_enable_differs():
    m, client = run_module(_params(enable=False), search_returns=[{"rules": [RULE]}])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.update_event_rule.assert_called_once()


def test_delete_when_exists():
    m, client = run_module(_params(state="absent"), search_returns=[{"rules": [RULE]}])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_event_rule.assert_called_once_with("dp-1_disconnected")


def test_delete_absent_when_missing_is_noop():
    m, client = run_module(_params(state="absent"), search_returns=[{"rules": []}])
    assert m.exit_json.call_args[1]["changed"] is False
    client.delete_event_rule.assert_not_called()


def test_query_returns_rules():
    m, client = run_module(_params(state="query"), search_returns=[{"rules": [RULE]}])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert kwargs["rules"] == [RULE]


def test_check_mode_blocks_create():
    m, client = run_module(_params(), check_mode=True, search_returns=[{"rules": []}])
    assert m.exit_json.call_args[1]["changed"] is True
    client.create_event_rule.assert_not_called()


def test_create_without_conditions_fails():
    try:
        run_module(_params(conditions=None), search_returns=[{"rules": []}])
    except SystemExit:
        pass
