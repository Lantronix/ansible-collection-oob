=========
Changelog
=========

.. contents:: Topics

v1.0.20
=======

Release Summary
---------------

Playbook correctness release. Removes two deprecated-module playbooks
(``percepxion_aoob_session.yml``, ``percepxion_users.yml``), strips deprecated
``percepxion_aoob_session`` calls from the incident response combo playbook,
corrects the device import field schema in the fleet onboarding combo playbook,
and fixes two runtime bugs where ``ansible.builtin.debug`` ``var:`` received a
Jinja2 expression instead of a plain variable name.

Bugfixes
--------

- ``playbooks/percepxion/percepxion_aoob_session.yml``: removed (entire file
  calls the ``percepxion_aoob_session`` module deprecated in v1.0.18).
- ``playbooks/percepxion/percepxion_users.yml``: removed (entire file calls
  the ``percepxion_users`` module deprecated in v1.0.18).
- ``playbooks/combo/incident_response_oob.yml``: removed Phase 2 (open
  session) and Phase 3 (close session) task blocks, which called the
  deprecated ``percepxion_aoob_session`` module. Playbook is now scoped to
  OOB path verification only; operators are directed to the Percepxion web UI
  for AOOB terminal sessions.
- ``playbooks/combo/new_device_fleet_onboarding.yml``: corrected the example
  ``devices`` list from pre-v1.0.18 field names (``serial``, ``mac``,
  ``model``) to the current schema (``device_id``, ``device_key``,
  ``device_name``, ``device_description``).
- ``playbooks/percepxion/percepxion_jobs.yml``: fixed ``ansible.builtin.debug``
  task using ``var:`` with a Jinja2 expression (``"{{ operation + '_result' }}"``).
  The ``var:`` parameter accepts a plain variable name only; replaced with
  ``msg: "{{ vars[operation + '_result'] | default({}) }}"``.
- ``playbooks/percepxion/percepxion_smart_groups.yml``: fixed
  ``ansible.builtin.debug`` task using ``var:`` with a Jinja2 ternary
  expression. Replaced with ``msg:`` using ``vars[...]`` dynamic lookup.

v1.0.19
=======

Release Summary
---------------

Lint cleanup release. Fixes ansible-lint ``name[template]`` violations across
11 task names in 7 playbooks, moves the example inventory template from
``playbooks/`` to ``examples/`` to resolve a false-positive syntax-check error
from ansible-lint, and updates the README module count and table to reflect
the two modules deprecated in v1.0.18.

Minor Changes
-------------

- ``examples/inventory.yml``: moved from ``playbooks/inventory.yml`` to
  eliminate an ansible-lint ``syntax-check`` false positive (ansible-lint
  treats all files in ``playbooks/`` as playbooks).
- Playbooks: fixed ``name[template]`` ansible-lint violations in
  ``day1_slc_onboarding.yml``, ``new_device_fleet_onboarding.yml``,
  ``percepxion_audit_logs.yml``, ``percepxion_import_devices.yml``,
  ``percepxion_projects.yml``, ``percepxion_smart_groups.yml``,
  ``slc_device_ports.yml``, and ``slc_managed_devices.yml``. Task names
  with Jinja2 templates now place the template at the end of the name string.
- ``README.md``: corrected module count from 20 to 18 active; marked
  ``percepxion_users`` and ``percepxion_aoob_session`` as deprecated in the
  module table.

v1.0.18
=======

Release Summary
---------------

Bugfix and deprecation release. Fixes the ``percepxion_import_devices`` device
field names introduced in v1.0.17, corrects the log download API field name in
``percepxion_audit_logs``, updates the unit test fixture for
``percepxion_import_devices`` to use correct field names, and deprecates
``percepxion_aoob_session`` and ``percepxion_users`` whose underlying API
endpoints are not present in the Percepxion 6.12 specification.

Bugfixes
--------

- ``lantronix.oob.percepxion_import_devices``: the module's
  ``argument_spec`` and ``DOCUMENTATION`` declared ``serial``, ``mac``, and
  ``model`` as the per-device suboption keys. The Percepxion
  ``DeviceRegisterRequest`` schema requires ``device_id`` (serial number),
  ``device_key`` (32-character device identifier), ``device_name``, and
  optionally ``device_description``. Any playbook that called
  ``register_device`` (not the idempotency skip path) would fail with an
  API 400. Fixed field names throughout the module, playbook, and unit test
  fixture.
- ``lantronix.oob.percepxion_audit_logs``: ``download_device_log`` sent
  ``log_type: "access"`` in the request body. The Percepxion 6.12
  ``DeviceLogDownloadRequest`` schema uses ``log_level`` (enum: ``info``).
  Fixed the client method signature, the caller in ``percepxion_audit_logs``,
  and the corresponding unit test assertion.

Deprecated Features
-------------------

- ``lantronix.oob.percepxion_aoob_session``: deprecated. The session
  management endpoints (``/v3/device/connect``, ``/v3/device/disconnect``)
  are not present in the Percepxion 6.12 API specification. The Percepxion
  Connect feature is browser-based and cannot be managed programmatically
  via these endpoints. The module will be removed in version 2.0.0. Use
  the Percepxion web interface to initiate AOOB terminal sessions.
- ``lantronix.oob.percepxion_users``: deprecated. The user management
  endpoints (``/v2/user/search``, ``/v2/user/create``, ``/v2/user/delete``)
  are not present in the Percepxion 6.12 API specification and returned 404
  during integration testing. The module will be removed in version 2.0.0.
  Use the Percepxion web interface to manage users.

v1.0.17
=======

Release Summary
---------------

Bugfix and cleanup release. Fixes a key name mismatch in ``slc_managed_devices``
where the module parsed ``managed_devices`` from the API response but the SLC9000
REST API v2 returns ``devices``. Fixes SLC9 httpapi raw socket session management
for mini_httpd compatibility. Excludes integration test config files from the
collection tarball. Removes internal identifiers from code comments.

Bugfixes
--------

- ``lantronix.oob.slc_managed_devices``: the module extracted ``managed_devices``
  from the ``/devices/managed`` API response, but the SLC9000 REST API v2 returns
  the list under the ``devices`` key. All ``slc_managed_devices`` tasks returned
  an empty list. Fixed response key to ``devices``.
- ``lantronix.oob.slc9`` httpapi plugin: raw socket session lifecycle (login,
  write, logout) refactored to bypass mini_httpd's split-header behaviour that
  caused connection failures when the SLC9000 web server processed HTTP headers
  across multiple TCP segments.
- ``galaxy.yml``: added ``tests/integration/integration_config.yml`` and
  ``tests/integration/integration_config.vault.yml`` to ``build_ignore`` so
  lab environment credentials are never bundled into the Automation Hub tarball.

Minor Changes
-------------

- Integration test targets: ``UNTESTED STATES`` blocks updated with
  post-reregistration findings for the AOOB session target; ``gen_inventory.py``
  now passes ``percepxion_project_tag`` to the write-lane Percepxion host.
- CI: added ``pytest`` and ``pytest-xdist`` to the unit test job dependencies.

v1.0.16
=======

Release Summary
---------------

Functional validation release. Adds a comprehensive four-tier integration
test system across all 20 modules. Tier 1/2 targets updated with explicit
``delegate_to:`` directives and ``UNTESTED STATES`` coverage documentation.
Four new SLC write-lane targets (``slc_system_write``, ``slc_users_write``,
``slc_config_write``, ``slc_network_write``) exercise full CRUD cycles against
the write lane. Five new Percepxion write-lane targets and three Tier 4
physical-device targets (``slc_device_ports_write``, ``slc_managed_devices_write``,
``percepxion_aoob_session_write``) validate managed-device and AOOB session
flows against a console-connected managed device. Bug regression tests B-1
(``percepxion_config`` name-only idempotency) and B-2 (``percepxion_smart_groups``
``query_string`` idempotency) added inline to existing targets.

Minor Changes
-------------

- All 20 integration test targets: added explicit ``delegate_to:`` on every
  module task. Four-host inventory (``slc9000``, ``slc9000-write``,
  ``percepxion-primary``, ``percepxion-write``) requires explicit delegation;
  implicit single-host resolution is unreliable with multiple hosts in play.
- All 20 integration test targets: added ``UNTESTED STATES`` comment blocks
  documenting known coverage gaps and deferred test scenarios.
- ``percepxion_audit_logs``, ``percepxion_devices``, ``percepxion_firmware``,
  ``percepxion_import_devices`` integration tests: replaced hardcoded internal
  hostnames and serial numbers with inventory variable references
  (``{{ slc_read_hostname }}``, ``{{ slc_read_serial }}``) so tests run without
  exposing lab device identifiers.
- New ``slc_system_write`` target: full write cycle, baseline read, check_mode,
  description set, idempotency, modify, revert, against the write lane.
- New ``slc_users_write`` target: password change cycle (check_mode → change →
  revert) using ``TestPass1234!`` as the intermediate value.
- New ``slc_config_write`` target: NTP server batch cycle (check_mode → add
  192.0.2.100 → idempotency → add 192.0.2.101 → remove both) using RFC 5737
  documentation-range IPs to avoid touching live NTP infrastructure.
- New ``slc_network_write`` target: MTU cycle on eth1 (check_mode mtu=1400 →
  set → idempotency → modify mtu=1350 → restore baseline).
- New ``percepxion_users_write`` target: role preflight via ``percepxion_facts``,
  check_mode create (role-constraint smoke test), absent idempotency on
  non-existent user.
- New ``percepxion_projects_write`` target: device lookup by write-lane hostname,
  check_mode project assignment.
- New ``percepxion_import_devices_write`` target: check_mode with synthetic
  serial ``CI-TEST-FAKE-SERIAL-001``; verifies check_mode reporting without
  touching device registry.
- New ``percepxion_jobs_write`` target: ``state: query`` smoke test asserting
  ``jobs`` key is iterable and ``changed=false``.
- New ``percepxion_firmware_write`` target: check_mode ``state: update`` and
  ``state: check`` compliance report against write lane.
- New ``slc_device_ports_write`` target (Tier 4): managed device reachability
  gate; structural comparison of port 1 (device connected) vs port 2 (empty).
- New ``slc_managed_devices_write`` target (Tier 4): asserts managed device
  appears in the managed device list on the expected port with required
  attributes (``port``, ``connection_state``).
- New ``percepxion_aoob_session_write`` target (Tier 4): full open/close AOOB
  session cycle; device_id looked up dynamically via ``percepxion_devices``;
  ``session_id`` verified on open and passed to close.
- ``percepxion_config`` integration test: added check_mode block and B-1
  regression block (name-only idempotency via ``percepxion-write`` lane).
- ``percepxion_smart_groups`` integration test: added check_mode block and B-2
  regression block (``query_string`` idempotency via ``percepxion-write`` lane).

v1.0.15
=======

Release Summary
---------------

Certification fix. Excludes ``.ansible/`` from the published collection tarball
via ``build_ignore`` in ``galaxy.yml`` and reverts inadvertent executable bits
set on module files in v1.0.14. No functional changes to modules, plugins,
or roles.

Bugfixes
--------

- ``galaxy.yml``: added ``.ansible/`` to ``build_ignore`` so
  ``ansible-test sanity`` output cached in the dev environment is not bundled
  into the Automation Hub tarball.
- ``plugins/modules/*.py``: reverted executable bit set in v1.0.14.
  Red Hat certification sanity requires module files to be non-executable
  (``shebang`` check enforces this).

v1.0.14
=======

Release Summary
---------------

Certification fix. Sets the executable bit on module files and expands
``build_ignore`` shebang entries to cover ansible-core 2.16 through 2.18.

Bugfixes
--------

- ``plugins/modules/*.py``: set executable bit so the ``shebang`` sanity
  check passes on the Red Hat certification pipeline (reverted in v1.0.15
  after discovering the check requires the opposite).
- ``galaxy.yml``: added ``build_ignore`` entries for sanity test output
  directories under ansible-core 2.16, 2.17, and 2.18 paths.

v1.0.13
=======

Release Summary
---------------

Sanity CI fix. Adds ``build_ignore`` entries for ansible-core 2.16, 2.17,
and 2.18 shebang ignore files so ``ansible-test sanity`` passes cleanly
across all targeted ansible-core versions.

Bugfixes
--------

- ``galaxy.yml``: added ``build_ignore`` entries for shebang ignore files
  generated under ansible-core 2.16, 2.17, and 2.18 test output paths.

v1.0.12
=======

Release Summary
---------------

Addresses Red Hat Automation Hub review findings from v1.0.11 certification.
Adds ``build_ignore`` to ``galaxy.yml`` to exclude development artifacts
(``.pytest_cache``, ``ansible.cfg``, ``validate/``, old tarballs, and
dev-environment files) from the published collection tarball. No functional
changes to modules, plugins, or roles.

v1.0.11
=======

Release Summary
---------------

Adds role metadata and updates README Support section per Red Hat certification
feedback. Adds ``meta/main.yml`` to all four roles so descriptions appear
correctly on Automation Hub. Updates Support section to list the Automation Hub
"Create issue" link as the primary support channel for Red Hat customers.

v1.0.10
=======

Release Summary
---------------

Strips executable bit from all collection files. WSL filesystem artifact caused
all files to appear executable, failing the ansible-test sanity ``shebang`` check
on the Red Hat certification pipeline.

v1.0.9
======

Release Summary
---------------

Adds missing ``README.md`` files to ``oob_baseline_config``, ``oob_firmware_audit``,
and ``oob_user_management`` roles. Required by Red Hat Automation Hub galaxy-importer.

v1.0.8
======

Release Summary
---------------

Red Hat certification compliance fixes. Adds missing ``LICENSE`` file (Apache 2.0),
``requirements.txt`` declaring the ``requests`` dependency, and ``.ansible-lint``
configuration for ``--profile=production`` CI validation. Bumps ``requires_ansible``
to ``>=2.16.0`` (ansible-core 2.14 is EOL). Fixes role variable naming to use full
role-name prefixes per ansible-lint production rules, replaces bare module names with
FQCN in role tasks, and corrects invalid Jinja2 syntax in ``oob_baseline_config``.

Minor Changes
-------------

- ``.ansible-lint`` - Added production profile config excluding ``tests/``, ``changelogs/``, ``validate/``, and ``.github/`` directories.
- ``LICENSE`` - Added Apache 2.0 license file at collection root (required by galaxy-importer).
- ``galaxy.yml`` - Fixed tag format: ``console-server`` and ``serial-console`` changed to ``console_server`` and ``serial_console`` (hyphens not allowed).
- ``meta/runtime.yml`` - Bumped ``requires_ansible`` from ``>=2.14.0`` to ``>=2.16.0``.
- ``requirements.txt`` - Added to declare ``requests`` as a Python dependency.
- Roles - Renamed all role variables to use the full ``<role_name>_`` prefix convention required by ansible-lint production profile.
- Roles - Replaced bare module names (``debug``, ``copy``) with FQCN (``ansible.builtin.debug``, ``ansible.builtin.copy``) in role tasks.
- ``roles/oob_baseline_config`` - Fixed invalid Jinja2 list comprehension syntax; replaced with ``map('regex_replace')`` filter.
- ``roles/oob_fleet_inventory`` - Added ``mode: "0644"`` to the inventory file write task.

v1.0.7
======

Release Summary
---------------

Integration test validation release. Fixes all 12 Percepxion integration test
targets against the Percepxion 6.12 demo environment. Adds Red Hat partner
certification workflow. Moves canonical repository to
``github.com/Lantronix/ansible-collection-oob``.

Bugfixes
--------

- All 12 Percepxion integration test targets: ``tenant_id`` must be passed
  explicitly in every task because ``connection.get_tenant_id()`` returns
  ``None`` in module context. Added ``tenant_id: "{{ percepxion_tenant_id }}"``
  to every Percepxion module task.
- ``percepxion_devices`` integration test: search string updated to match a
  device confirmed registered in the demo tenant.
- ``percepxion_smart_groups`` integration test: replaced ``criteria`` dict
  parameter (rejected by module) with ``query_string`` string parameter
  matching the module's ``argument_spec``.
- ``percepxion_firmware`` integration test: same ``criteria`` → ``query_string``
  fix applied to the embedded temporary smart group creation task.
- ``percepxion_import_devices`` integration test: corrected serial number to a
  device confirmed registered in the demo tenant for the idempotency (skip)
  path; added ``check_mode: true`` path for the would-register scenario.
- ``percepxion_jobs`` integration test: rewritten as read-only ``state: query``
  smoke test. The ``/v1/job/jobgroup/create`` endpoint requires a full
  operation payload (``type``, ``subtype``, ``op_code``, ``operation``,
  ``device_id``) not supported by the module's current create interface; full
  CRUD coverage lives in unit tests.
- ``percepxion_aoob_session`` integration test: rewritten as ``check_mode: true``
  smoke test. Live ``/v3/device/connect`` calls require the physical device to
  hold an active Percepxion device token; the lab SLC9000 devices were not
  actively registered, returning "Invalid device token size". Module decision
  logic and check_mode reporting are verified without a live connection.

Minor Changes
-------------

- ``galaxy.yml``: repository, documentation, and issues URLs updated from
  ``github.com/What-Is-Phase-Two`` to ``github.com/Lantronix``.
- ``.github/workflows/certification.yml``: added Red Hat partner certification
  checker workflow (``ansible-collections/partner-certification-checker@v1``).
  Runs on every push and pull request to ``main``.

v1.0.6
======

Release Summary
---------------

Bugfix release. Corrects ``slc_firmware`` module parameter declarations and
``SLC9Client`` API payload field names found during end-to-end firmware update
testing against the SLC9000 R9 lab device.

Bugfixes
--------

- ``lantronix.oob.slc_firmware``: module ``argument_spec`` was missing
  ``md5_key``, ``reboot_after_update``, and ``description`` parameters declared
  in the module's ``DOCUMENTATION``. Ansible rejected any playbook that passed
  these values with "Unsupported parameters" errors. Fixed by adding all three
  to the spec with correct types and defaults. Removed the unused ``bank``
  parameter. ``required_if`` now enforces that both ``url`` and ``md5_key`` are
  provided when ``state: update``.
- ``lantronix.oob.slc_firmware``: the firmware trigger call passed ``bank``
  (undeclared, ignored by the API) to ``trigger_firmware_update()``. Call now
  passes ``file_url``, ``md5_key``, ``reboot_after_update``, and ``description``
  matching the actual SLC9000 ``POST /firmware/update`` contract.
- ``SLC9Client.trigger_firmware_update()``: API payload used ``url`` and ``bank``
  keys. The SLC9000 REST API v2 requires ``file_url`` (URL to the ``.tgz``
  file server path) and ``key`` (MD5 checksum string). Fixed field names to
  match the OpenAPI spec; removed ``bank`` (firmware is always written to the
  alternate boot bank). Added ``reboot_after_update`` and ``description`` fields.
- ``SLC9Client._get()``: a non-JSON response body (device returning an HTML error
  page during firmware flash or reboot) raised an unhandled ``ValueError``. Added
  ``except ValueError`` with a message that includes the HTTP status code and the
  first 200 bytes of the body for easier diagnosis.

v1.0.5
======

Release Summary
---------------

Enhancement release. Adds ``percepxion_api_host`` inventory variable so the
Percepxion API URL hostname can differ from the TCP connection target
(``ansible_host``). Enables on-premises split-DNS deployments and switching
between ``api.percepxion.ai`` (production) and ``api.gopercepxion.ai``
(demo/sandbox) without changing the inventory host entry.

Minor Changes
-------------

- ``lantronix.oob.percepxion`` httpapi plugin: added ``percepxion_api_host``
  plugin option (``vars: - name: percepxion_api_host``). When set, this
  hostname is used to construct all Percepxion API URLs
  (``https://<percepxion_api_host>/api/...``) instead of ``ansible_host``.
  Added ``get_api_host()`` method on ``HttpApi`` used by ``login()`` and
  all 12 Percepxion modules.
- All 12 Percepxion modules: replaced ``connection.get_option("host")`` with
  ``connection.get_api_host()`` so the ``percepxion_api_host`` variable is
  honoured throughout the module lifecycle, not just at login.

v1.0.4
======

Release Summary
---------------

Bugfix release. Corrects API payload formats discovered during end-to-end
integration testing against the Percepxion 6.12 demo environment and the
SLC9000 R8 lab device. Fixes ``ansible-test sanity`` failures blocking
Red Hat certification submission.

Bugfixes
--------

- ``lantronix.oob.percepxion`` httpapi plugin: ``login()`` now uses
  ``requests`` directly instead of netcommon's ``send()``. When ``_auth``
  is ``None``, netcommon injects an ``Authorization: Basic`` header into
  every request including the login POST itself. Percepxion's API, when
  receiving login credentials with an extra Basic auth header, issues a
  token that is immediately invalid, causing all subsequent calls to fail
  with 401. Using ``requests`` in ``login()`` bypasses this injection.
- ``lantronix.oob.slc9`` httpapi plugin: same ``login()`` fix as Percepxion
  to maintain consistency and avoid future Basic-auth injection issues.
- All 12 Percepxion modules: ``connection.get_option("percepxion_project_tag")``
  and ``connection.get_option("percepxion_tenant_id")`` fail with "Internal
  error" because JSON-RPC proxying from modules only covers standard connection
  options. Fixed by reading these values from ``module.params`` instead and
  adding ``project_tag`` and ``tenant_id`` to each module's ``argument_spec``.
- ``percepxion_client.search_smart_groups()``: added required ``limit``
  parameter to request body (API returns 400 if ``limit`` is missing).
- ``percepxion_client.create_smart_group()``: changed from ``criteria`` dict
  format to ``query_string`` string format matching the actual API. Old format
  caused 400 "Must specify either query_string or array of device_id".
- ``percepxion_client.delete_smart_group()``: changed payload from
  ``{"group_id": id}`` to ``{"id": [id]}`` (array) to match the API.
- ``percepxion_client.search_job_groups()``: added required ``limit`` parameter.
- ``percepxion_client.create_content()``: the content API uses multipart/form-data
  upload (not JSON). Rewrote to use multipart with ``file`` and ``data`` fields,
  bypassing the session's ``Content-Type: application/json`` header.
- ``percepxion_client.search_content()``: added required ``limit`` parameter.
- ``percepxion_client.delete_content()``: changed from ``{"content_id": id}``
  to ``{"id": [id]}`` array format.
- ``percepxion_client.search_users()``: added ``limit`` parameter; corrected
  endpoint from ``/v3/user/search`` to ``/v2/user/search``.
- ``percepxion_client.create_user()``, ``delete_user()``: corrected endpoints
  from ``/v3/`` to ``/v2/`` prefix.
- ``percepxion_client.get_device()``: API requires ``device_id`` as a list
  (``[device_id]``) not a bare string; now returns ``result[0]`` for transparency.
- ``percepxion_client.unassign_device()``: ``device_id`` must be a list.
- Multiple Percepxion modules: fixed response key parsing, ``search_results``
  → ``result`` (content, users), ``search_result`` (smart groups),
  ``total_results`` is correct for device search; ``id`` instead of
  ``group_id`` / ``content_id`` in creation responses.
- ``lantronix.oob.slc_network``: fixed ``_find_interface()`` to parse SLC API's
  flat-key response format (``eth1_ipv4``, ``eth1_mask`` etc.) instead of
  expecting a list. Fixed write payload to use the same flat-key format.
- ``lantronix.oob.slc_firmware``: corrected API endpoint from
  ``/firmware/version`` (404) to ``/firmware/status``.
- ``plugins/httpapi/percepxion.py``, ``slc9.py``: wrapped ``import requests``
  in ``try/except ImportError`` with ``HAS_REQUESTS`` guard so
  ``ansible-test sanity --test import`` passes without ``requests`` installed.
- All unit tests: replaced ``unnecessary-lambda`` ``side_effect`` patterns
  with direct ``dict.get`` method references; renamed bare ``_`` unpack
  variables to ``mock_cls`` to satisfy ``pylint disallowed-name`` rule;
  fixed ``E501`` line-length violations in ``side_effect`` assignments.

v1.0.3
======

Release Summary
---------------

Bugfix release. Fixes a fundamental authentication timing issue where modules
always received a ``None`` token from the httpapi plugin.

Bugfixes
--------

- ``lantronix.oob.slc9`` and ``lantronix.oob.percepxion`` httpapi plugins: modules
  call ``get_token()`` before any ``send()`` has occurred, so the
  ``@ensure_connect`` decorator (which triggers ``_connect()`` and ``login()``)
  was never fired. All 20 modules silently received a ``None`` token and every
  API call failed with a 401 from the device. Fixed by having ``get_token()`` (and
  ``get_csrf_token()``) issue a lightweight ``send()`` call when ``_auth`` is
  ``None``, forcing the connection and login to complete before the token is
  returned
  (https://github.com/Lantronix/ansible-collection-oob/issues/3).

v1.0.2
======

Release Summary
---------------

Bugfix release. Corrects the SLC9000 authentication header name used for all
API calls after login.

Bugfixes
--------

- ``lantronix.oob.slc9`` httpapi plugin and ``SLC9Client``: changed authentication
  header from ``x-user-token`` to ``X-auth-token`` to match the SLC9000 REST API
  v2 security scheme. All SLC module tasks previously failed with
  "Invalid or expired authentication tokens" on every API call despite successful
  login, because the session token was sent under the wrong header name
  (https://github.com/Lantronix/ansible-collection-oob/issues/2).

v1.0.1
======

Release Summary
---------------

Bugfix release. Corrects SSL certificate validation behavior when
``ansible_httpapi_validate_certs: false`` is set in inventory.

Bugfixes
--------

- All 20 modules now correctly read the ``validate_certs`` connection option and
  pass it to the underlying ``requests.Session`` as ``verify_ssl``. Previously,
  the option was silently ignored and all modules defaulted to
  ``verify_ssl=True``, causing ``SSLError`` failures against devices with
  self-signed certificates even when ``ansible_httpapi_validate_certs: false``
  was set (https://github.com/Lantronix/ansible-collection-oob/issues/1).

v1.0.0
======

Release Summary
---------------

Initial release of the ``lantronix.oob`` Ansible collection. Provides 20 modules,
two httpapi connection plugins, and four example roles covering the full
Lantronix Out-of-Band infrastructure stack: SLC9000 console servers and the
Percepxion 6.12+ fleet management platform.

New Plugins
-----------

Connection
~~~~~~~~~~

- ``lantronix.oob.slc9`` - HttpApi plugin for SLC9000 REST API v2 (R8+).
  Handles session-token authentication against the device-local API.
- ``lantronix.oob.percepxion`` - HttpApi plugin for Percepxion REST API (6.12+).
  Handles Bearer token and CSRF token authentication against the cloud API.

New Modules
-----------

SLC9000 Device Modules
~~~~~~~~~~~~~~~~~~~~~~~

- ``lantronix.oob.slc_facts`` - Gather hardware, firmware, and status facts
  from a Lantronix SLC9000 device.
- ``lantronix.oob.slc_users`` - Manage local user accounts on an SLC9000.
- ``lantronix.oob.slc_network`` - Configure Ethernet interfaces on an SLC9000.
- ``lantronix.oob.slc_system`` - Manage hostname, NTP, timezone, and reboot
  an SLC9000.
- ``lantronix.oob.slc_device_ports`` - Query serial and console port
  configuration on an SLC9000.
- ``lantronix.oob.slc_firmware`` - Check firmware version and trigger firmware
  upgrades on an SLC9000.
- ``lantronix.oob.slc_config`` - Back up, compare, batch commands, and save
  configuration on an SLC9000.
- ``lantronix.oob.slc_managed_devices`` - Query devices connected via serial
  ports on an SLC9000.

Percepxion Fleet Modules
~~~~~~~~~~~~~~~~~~~~~~~~

- ``lantronix.oob.percepxion_facts`` - Gather fleet summary and platform facts
  from a Percepxion instance.
- ``lantronix.oob.percepxion_devices`` - Query and update device inventory in
  Percepxion.
- ``lantronix.oob.percepxion_projects`` - Manage device project assignments in
  Percepxion.
- ``lantronix.oob.percepxion_users`` - Manage Percepxion users and roles.
- ``lantronix.oob.percepxion_smart_groups`` - Create and manage device smart
  groups in Percepxion.
- ``lantronix.oob.percepxion_firmware`` - Generate fleet firmware compliance
  reports and trigger upgrades via Percepxion.
- ``lantronix.oob.percepxion_config`` - Back up, restore, and push
  configuration at fleet scale via Percepxion.
- ``lantronix.oob.percepxion_jobs`` - Manage job group lifecycle (create,
  schedule, monitor) in Percepxion.
- ``lantronix.oob.percepxion_audit_logs`` - Query security audit logs and
  export device access logs from Percepxion.
- ``lantronix.oob.percepxion_aoob_session`` - Initiate and terminate Out-of-Band
  terminal sessions via Percepxion.
- ``lantronix.oob.percepxion_import_devices`` - Bulk import devices and assign
  them to projects in Percepxion.
- ``lantronix.oob.percepxion_telemetry`` - Retrieve device telemetry statistics
  and historical data from Percepxion.

New Roles
---------

- ``lantronix.oob.oob_fleet_inventory`` - Query Percepxion and generate a
  dynamic Ansible inventory file.
- ``lantronix.oob.oob_firmware_audit`` - Check fleet firmware compliance and
  optionally trigger upgrades.
- ``lantronix.oob.oob_user_management`` - Bulk user management across all SLC
  devices in a Percepxion smart group.
- ``lantronix.oob.oob_baseline_config`` - Enforce baseline hostname, NTP, and
  syslog configuration across an SLC fleet.
