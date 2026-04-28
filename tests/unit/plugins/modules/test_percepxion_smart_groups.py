from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_smart_groups

EXISTING_GROUP = {"search_results": [{"group_id": "grp-001", "name": "dc1-servers", "criteria": {}}]}
NO_GROUPS = {"search_results": []}


def run_module(params, check_mode=False, search_result=None):
    result = search_result if search_result is not None else NO_GROUPS
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_smart_groups.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_smart_groups.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_smart_groups.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_smart_groups.return_value = result
                instance.create_smart_group.return_value = {"group_id": "grp-002"}
                instance.delete_smart_group.return_value = {}
                mock_cls.return_value = instance

                mock_conn = MagicMock()
                mock_conn.get_token.return_value = "test-token"
                mock_conn.get_csrf_token.return_value = "test-csrf"
                mock_conn.get_option.return_value = None
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_smart_groups.main()
                return m, instance


def test_create_when_missing():
    m, client = run_module({"name": "dc1-servers", "criteria": {"tag": "dc1"}, "state": "present"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_smart_group.assert_called_once_with("dc1-servers", {"tag": "dc1"})


def test_no_change_when_exists():
    m, client = run_module(
        {"name": "dc1-servers", "criteria": {}, "state": "present"},
        search_result=EXISTING_GROUP,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_smart_group.assert_not_called()


def test_delete_removes_group():
    m, client = run_module(
        {"name": "dc1-servers", "criteria": None, "state": "absent"},
        search_result=EXISTING_GROUP,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_smart_group.assert_called_once_with("grp-001")


def test_check_mode_blocks_create():
    m, client = run_module(
        {"name": "new-group", "criteria": {"tag": "x"}, "state": "present"},
        check_mode=True,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_smart_group.assert_not_called()
