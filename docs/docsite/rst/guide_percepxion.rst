.. _guide_percepxion:

Percepxion Guide
================

The ``lantronix.oob`` collection manages Lantronix Percepxion 6.12+ fleet
infrastructure via the Percepxion cloud API.

.. contents::
   :local:
   :depth: 2

Connection Setup
----------------

Percepxion modules use the ``ansible.netcommon.httpapi`` connection with the
``lantronix.oob.percepxion`` network OS plugin. The API host is
``api.consoleflow.com`` for the Percepxion SaaS platform. Configure your
inventory:

.. code-block:: yaml

   percepxion:
     hosts:
       percepxion_platform:
         ansible_host: api.consoleflow.com
     vars:
       ansible_network_os: lantronix.oob.percepxion
       ansible_connection: ansible.netcommon.httpapi
       ansible_httpapi_use_ssl: true
       ansible_user: "{{ vault_percepxion_user }}"
       ansible_password: "{{ vault_percepxion_password }}"
       percepxion_project_tag: "prod-datacenter-east"   # optional
       percepxion_tenant_id: "34f5c98e-..."             # optional — Project Admin only

Authentication
--------------

The ``lantronix.oob.percepxion`` plugin logs in via ``POST /v2/user/login``
and caches both the ``x-mystq-token`` and ``x-csrf-token`` from the response.
Both tokens are injected on all subsequent requests. You do not manage tokens
directly.

A 403 response may indicate an expired session. Re-run the playbook; the
plugin will re-authenticate automatically.

Project and Tenant Scoping
---------------------------

Percepxion supports multi-project and multi-tenant deployments.

- ``percepxion_project_tag`` scopes all device operations to a named project.
- ``percepxion_tenant_id`` is required only when authenticating as a Project Admin.

Set these as inventory connection variables. All Percepxion modules inherit
them automatically. To operate across multiple projects, loop over inventory
groups rather than passing project identifiers as module arguments.

Available Modules
-----------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - Module
     - Description
   * - :ref:`lantronix.oob.percepxion_facts <ansible_collections.lantronix.oob.percepxion_facts_module>`
     - Gather fleet summary and platform facts
   * - :ref:`lantronix.oob.percepxion_devices <ansible_collections.lantronix.oob.percepxion_devices_module>`
     - Query and update device inventory
   * - :ref:`lantronix.oob.percepxion_projects <ansible_collections.lantronix.oob.percepxion_projects_module>`
     - Manage device project assignments
   * - :ref:`lantronix.oob.percepxion_users <ansible_collections.lantronix.oob.percepxion_users_module>`
     - Manage Percepxion users and roles
   * - :ref:`lantronix.oob.percepxion_smart_groups <ansible_collections.lantronix.oob.percepxion_smart_groups_module>`
     - Create and manage device smart groups
   * - :ref:`lantronix.oob.percepxion_firmware <ansible_collections.lantronix.oob.percepxion_firmware_module>`
     - Fleet firmware compliance report and upgrade
   * - :ref:`lantronix.oob.percepxion_config <ansible_collections.lantronix.oob.percepxion_config_module>`
     - Config backup, restore, push at fleet scale
   * - :ref:`lantronix.oob.percepxion_jobs <ansible_collections.lantronix.oob.percepxion_jobs_module>`
     - Job group lifecycle — create, schedule, monitor
   * - :ref:`lantronix.oob.percepxion_audit_logs <ansible_collections.lantronix.oob.percepxion_audit_logs_module>`
     - Security audit log query and device access log export
   * - :ref:`lantronix.oob.percepxion_aoob_session <ansible_collections.lantronix.oob.percepxion_aoob_session_module>`
     - Initiate and terminate OOB sessions
   * - :ref:`lantronix.oob.percepxion_import_devices <ansible_collections.lantronix.oob.percepxion_import_devices_module>`
     - Bulk device import and project assignment
   * - :ref:`lantronix.oob.percepxion_telemetry <ansible_collections.lantronix.oob.percepxion_telemetry_module>`
     - Device telemetry stats and historical data

Quick Start
-----------

.. code-block:: yaml

   - hosts: percepxion_platform
     gather_facts: false
     tasks:
       - name: Run firmware compliance report
         lantronix.oob.percepxion_firmware:
           state: report
         register: audit

       - name: Show non-compliant devices
         ansible.builtin.debug:
           msg: "Non-compliant: {{ audit.firmware_report.non_compliant | map(attribute='device_name') | list }}"

Fleet Inventory Generation
---------------------------

The ``oob_fleet_inventory`` role queries Percepxion and writes a dynamic
Ansible inventory file:

.. code-block:: yaml

   - hosts: percepxion_platform
     gather_facts: false
     roles:
       - role: lantronix.oob.oob_fleet_inventory
         vars:
           oob_inventory_output_path: /etc/ansible/oob-inventory.yml
           oob_inventory_limit: 1000

Percepxion Version Requirements
--------------------------------

This collection requires **Percepxion 6.12 or later**. Earlier versions do not
support the v3 device API endpoints used by most Percepxion modules.

The ``lantronix.oob.percepxion_facts`` module returns the Percepxion platform
version. Check it early in your playbooks if version-gating is needed:

.. code-block:: yaml

   - name: Gather Percepxion facts
     lantronix.oob.percepxion_facts:
     register: pxn

   - name: Assert minimum version
     ansible.builtin.assert:
       that: pxn.percepxion_facts.version is version('6.12', '>=')
       msg: "Percepxion 6.12+ required"
