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
                _conn_opts = {"host": "api.consoleflow.com", "validate_certs": False}
                mock_conn.get_option.side_effect = _conn_opts.get
                mock_conn_cls.return_value = mock_conn

                m = MagicMock()
                m.params = params
                m.check_mode = check_mode
                m._socket_path = "/tmp/fake-socket"
                mock_mod.return_value = m

                percepxion_jobs.main()
                return m, instance, mock_cls


def test_creates_new_job_group():
    m, client, mock_cls = run_module({"name": "nightly-backup", "job_type": "backup", "enabled": True, "state": "present"})
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.create_job_group.assert_called_once()


def test_no_change_when_job_exists_and_enabled():
    m, client, mock_cls = run_module(
        {"name": "nightly-backup", "job_type": "backup", "enabled": True, "state": "present"},
        search_result=EXISTING_JOB,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    client.create_job_group.assert_not_called()


def test_disables_existing_job():
    m, client, mock_cls = run_module(
        {"name": "nightly-backup", "job_type": "backup", "enabled": False, "state": "present"},
        search_result=EXISTING_JOB,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is True
    client.enable_job_groups.assert_called_once_with(["jg-001"], enabled=False)


def test_query_returns_logs_unchanged():
    m, client, mock_cls = run_module(
        {"name": "nightly-backup", "job_type": None, "enabled": True, "state": "query"},
        search_result=EXISTING_JOB,
    )
    kwargs = m.exit_json.call_args[1]
    assert kwargs["changed"] is False
    assert "job_logs" in kwargs


def test_percepxion_jobs_passes_validate_certs_to_client():
    m, _instance, mock_cls = run_module({"name": "job1", "job_type": "backup", "enabled": True, "state": "present"})
    call_kwargs = mock_cls.call_args[1]
    assert "verify_ssl" in call_kwargs
    assert call_kwargs["verify_ssl"] is False
