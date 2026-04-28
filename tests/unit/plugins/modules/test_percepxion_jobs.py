from __future__ import absolute_import, division, print_function
__metaclass__ = type

from unittest.mock import patch, MagicMock
from ansible_collections.lantronix.oob.plugins.modules import percepxion_jobs

EXISTING_JOB = {"search_results": [{"job_group_id": "jg-001", "name": "nightly-backup", "enabled": True}]}
NO_JOBS = {"search_results": []}
MOCK_LOGS = {"job_logs": [{"job_group_id": "jg-001", "status": "success"}]}


def run_module(params, check_mode=False, search_result=None):
    result = search_result if search_result is not None else NO_JOBS
    with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_jobs.AnsibleModule") as mock_mod:
        with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_jobs.Connection") as mock_conn_cls:
            with patch("ansible_collections.lantronix.oob.plugins.modules.percepxion_jobs.PercepxionClient") as mock_cls:
                instance = MagicMock()
                instance.search_job_groups.return_value = result
                instance.create_job_group.return_value = {"job_group_id": "jg-002"}
                instance.delete_job_group.return_value = {}
                instance.enable_job_groups.return_value = {}
                instance.search_job_logs.return_value = MOCK_LOGS
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

                percepxion_jobs.main()
                return m, instance


def test_creates_new_job_group():
    m, client = run_module({"name": "nightly-backup", "job_type": "backup", "enabled": True, "state": "present"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_job_group.assert_called_once()


def test_no_change_when_job_exists_and_enabled():
    m, client = run_module(
        {"name": "nightly-backup", "job_type": "backup", "enabled": True, "state": "present"},
        search_result=EXISTING_JOB,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_job_group.assert_not_called()


def test_disables_existing_job():
    m, client = run_module(
        {"name": "nightly-backup", "job_type": "backup", "enabled": False, "state": "present"},
        search_result=EXISTING_JOB,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.enable_job_groups.assert_called_once_with(["jg-001"], enabled=False)


def test_query_returns_logs_unchanged():
    m, client = run_module(
        {"name": "nightly-backup", "job_type": None, "enabled": True, "state": "query"},
        search_result=EXISTING_JOB,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert "job_logs" in kwargs
