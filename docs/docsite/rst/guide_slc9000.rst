.. _guide_slc9000:

SLC 9000 Guide
==============

The ``lantronix.oob`` collection manages Lantronix SLC 9000 console servers
via the device-local REST API v2 (firmware R8+).

.. contents::
   :local:
   :depth: 2

Connection Setup
----------------

SLC 9000 modules use the ``ansible.netcommon.httpapi`` connection with the
``lantronix.oob.slc9`` network OS plugin. Configure this in your inventory:

.. code-block:: yaml

   slc_devices:
     hosts:
       slc9k-datacenter:
         ansible_host: 192.168.1.100
     vars:
       ansible_network_os: lantronix.oob.slc9
       ansible_connection: ansible.netcommon.httpapi
       ansible_httpapi_use_ssl: true
       ansible_httpapi_validate_certs: true
       ansible_user: sysadmin
       ansible_password: "{{ vault_slc_password }}"

Authentication
--------------

The ``lantronix.oob.slc9`` plugin logs in via ``POST /api/v2/user/login`` and
stores the session token in the ``x-user-token`` header for all subsequent
requests. You do not manage tokens directly; set ``ansible_user`` and
``ansible_password`` in your inventory.

Available Modules
-----------------

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Module
     - Description
   * - :ref:`lantronix.oob.slc_facts <ansible_collections.lantronix.oob.slc_facts_module>`
     - Gather hardware, firmware, and status facts
   * - :ref:`lantronix.oob.slc_users <ansible_collections.lantronix.oob.slc_users_module>`
     - Manage local user accounts
   * - :ref:`lantronix.oob.slc_network <ansible_collections.lantronix.oob.slc_network_module>`
     - Configure Ethernet interfaces
   * - :ref:`lantronix.oob.slc_system <ansible_collections.lantronix.oob.slc_system_module>`
     - Manage hostname, NTP, timezone, reboot
   * - :ref:`lantronix.oob.slc_device_ports <ansible_collections.lantronix.oob.slc_device_ports_module>`
     - Query serial and console port configuration
   * - :ref:`lantronix.oob.slc_firmware <ansible_collections.lantronix.oob.slc_firmware_module>`
     - Check firmware version and trigger upgrades
   * - :ref:`lantronix.oob.slc_config <ansible_collections.lantronix.oob.slc_config_module>`
     - Back up, compare, batch commands, and save config
   * - :ref:`lantronix.oob.slc_managed_devices <ansible_collections.lantronix.oob.slc_managed_devices_module>`
     - Query devices connected via serial ports

Quick Start
-----------

.. code-block:: yaml

   - hosts: slc_devices
     gather_facts: false
     tasks:
       - name: Gather SLC facts
         lantronix.oob.slc_facts:
         register: result

       - name: Show firmware version
         ansible.builtin.debug:
           msg: "{{ inventory_hostname }} running {{ result.slc_facts.firmware_version }}"

       - name: Enforce NTP server
         lantronix.oob.slc_system:
           ntp_servers:
             - 192.168.1.1
           state: present

       - name: Ensure sysadmin account exists
         lantronix.oob.slc_users:
           username: sysadmin
           role: admin
           state: present

Firmware Requirements
---------------------

SLC 9000 REST API v2 requires firmware **R8 or later** (9.7.0.0R8+). Earlier
firmware does not expose the v2 API endpoints used by this collection.

Check your firmware version:

.. code-block:: yaml

   - name: Check firmware
     lantronix.oob.slc_firmware:
       state: check
     register: fw

   - name: Warn if below minimum
     ansible.builtin.debug:
       msg: "WARNING: R8 firmware required"
     when: fw.firmware.current_version is version('9.7.0.0R8', '<')
