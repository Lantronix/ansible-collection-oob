=========
Changelog
=========

.. contents:: Topics

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
SLC 9000 R8 lab device. Fixes ``ansible-test sanity`` failures blocking
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
- Multiple Percepxion modules: fixed response key parsing — ``search_results``
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
  (https://github.com/What-Is-Phase-Two/ansible-collection-oob/issues/3).

v1.0.2
======

Release Summary
---------------

Bugfix release. Corrects the SLC 9000 authentication header name used for all
API calls after login.

Bugfixes
--------

- ``lantronix.oob.slc9`` httpapi plugin and ``SLC9Client``: changed authentication
  header from ``x-user-token`` to ``X-auth-token`` to match the SLC 9000 REST API
  v2 security scheme. All SLC module tasks previously failed with
  "Invalid or expired authentication tokens" on every API call despite successful
  login, because the session token was sent under the wrong header name
  (https://github.com/What-Is-Phase-Two/ansible-collection-oob/issues/2).

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
  was set (https://github.com/What-Is-Phase-Two/ansible-collection-oob/issues/1).

v1.0.0
======

Release Summary
---------------

Initial release of the ``lantronix.oob`` Ansible collection. Provides 20 modules,
two httpapi connection plugins, and four example roles covering the full
Lantronix Out-of-Band infrastructure stack: SLC 9000 console servers and the
Percepxion 6.12+ fleet management platform.

New Plugins
-----------

Connection
~~~~~~~~~~

- ``lantronix.oob.slc9`` - HttpApi plugin for SLC 9000 REST API v2 (R8+).
  Handles session-token authentication against the device-local API.
- ``lantronix.oob.percepxion`` - HttpApi plugin for Percepxion REST API (6.12+).
  Handles Bearer token and CSRF token authentication against the cloud API.

New Modules
-----------

SLC 9000 Device Modules
~~~~~~~~~~~~~~~~~~~~~~~

- ``lantronix.oob.slc_facts`` - Gather hardware, firmware, and status facts
  from a Lantronix SLC 9000 device.
- ``lantronix.oob.slc_users`` - Manage local user accounts on an SLC 9000.
- ``lantronix.oob.slc_network`` - Configure Ethernet interfaces on an SLC 9000.
- ``lantronix.oob.slc_system`` - Manage hostname, NTP, timezone, and reboot
  an SLC 9000.
- ``lantronix.oob.slc_device_ports`` - Query serial and console port
  configuration on an SLC 9000.
- ``lantronix.oob.slc_firmware`` - Check firmware version and trigger firmware
  upgrades on an SLC 9000.
- ``lantronix.oob.slc_config`` - Back up, compare, batch commands, and save
  configuration on an SLC 9000.
- ``lantronix.oob.slc_managed_devices`` - Query devices connected via serial
  ports on an SLC 9000.

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
