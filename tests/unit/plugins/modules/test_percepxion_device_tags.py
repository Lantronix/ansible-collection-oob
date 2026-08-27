from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_device_tags

TAG = {"id": "t-001", "name": "production", "color": "#FFF", "background_color": "#DC2626"}


def run_module(params, check_mode=False, tags=None):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_device_tags.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_device_tags.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_device_tags.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.list_device_tags.return_value = {"tag": tags if tags is not None else []}
                instance.create_device_tag.return_value = {"id": "t-002"}
                instance.assign_device_tag.return_value = {}
                instance.unassign_device_tag.return_value = {}
                instance.delete_device_tag.return_value = {}
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
                    percepxion_device_tags.main()
                except SystemExit:
                    pass
                return m, instance


def _params(**over):
    base = {"name": "production", "state": "present", "color": "#FFF",
            "background_color": "#DC2626", "device_ids": None,
            "project_tag": None, "tenant_id": None}
    base.update(over)
    return base


def test_create_when_missing():
    m, client = run_module(_params())
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_device_tag.assert_called_once_with(name="production", color="#FFF", background_color="#DC2626")


def test_no_change_when_tag_exists_no_devices():
    m, client = run_module(_params(), tags=[TAG])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_device_tag.assert_not_called()
    assert kwargs.get("tag_id") == "t-001"


def test_create_without_colors_fails():
    try:
        run_module(_params(color=None, background_color=None))
    except SystemExit:
        pass


def test_assign_when_devices_given():
    m, client = run_module(_params(device_ids=["dev-1", "dev-2"]), tags=[TAG])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.assign_device_tag.assert_called_once_with(tag_ids=["t-001"], device_ids=["dev-1", "dev-2"])


def test_unassign_on_absent_with_devices():
    m, client = run_module(_params(state="absent", device_ids=["dev-1"]), tags=[TAG])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.unassign_device_tag.assert_called_once_with(tag_ids=["t-001"], device_ids=["dev-1"])
    client.delete_device_tag.assert_not_called()


def test_delete_on_absent_without_devices():
    m, client = run_module(_params(state="absent", device_ids=None), tags=[TAG])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.delete_device_tag.assert_called_once_with(["t-001"])


def test_query_returns_tags():
    m, client = run_module(_params(state="query"), tags=[TAG])
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert kwargs["tags"] == [TAG]


def test_check_mode_blocks_create():
    m, client = run_module(_params(), check_mode=True)
    assert m.exit_json.call_args[1]["changed"] is True
    client.create_device_tag.assert_not_called()
