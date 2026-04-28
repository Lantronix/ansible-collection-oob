from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_projects


def _make_client(device_project_tag="project-a"):
    instance = MagicMock()
    instance.get_device.return_value = {"device_id": "dev-001", "project_tag": device_project_tag}
    instance.assign_device.return_value = {}
    instance.unassign_device.return_value = {}
    return instance


def run_module(params, check_mode=False, device_project_tag="project-a"):
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_projects.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_projects.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_projects.PercepxionClient") as mock_cls:
                instance = _make_client(device_project_tag)
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

                percepxion_projects.main()
                return m, instance


def test_no_change_when_already_assigned():
    m, client = run_module(
        {"device_id": "dev-001", "project_tag": "project-a", "state": "present"},
        device_project_tag="project-a",
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.assign_device.assert_not_called()


def test_changed_when_unassigned():
    m, client = run_module(
        {"device_id": "dev-001", "project_tag": "project-a", "state": "present"},
        device_project_tag=None,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.assign_device.assert_called_once()


def test_absent_removes_from_project():
    m, client = run_module(
        {"device_id": "dev-001", "project_tag": None, "state": "absent"},
        device_project_tag="project-a",
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.unassign_device.assert_called_once_with("dev-001")


def test_check_mode_blocks_assign():
    m, client = run_module(
        {"device_id": "dev-001", "project_tag": "project-a", "state": "present"},
        check_mode=True,
        device_project_tag=None,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.assign_device.assert_not_called()
