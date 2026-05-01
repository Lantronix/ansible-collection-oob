=========
Changelog
=========

.. contents:: Topics

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
