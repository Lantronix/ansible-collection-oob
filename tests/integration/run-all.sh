#!/usr/bin/env bash
# Run all integration targets in the standard DVT → DVT3 sequence.
# Usage: bash tests/integration/run-all.sh [dvt|dvt3|all]
# Default: all
#
# DVT lane  - read-only targets against 192.168.100.75 and api.gopercepxion.ai
# DVT3 lane - write targets against 192.168.100.76 and api.percepxion.ai
#             (runs setup_dvt3 first, teardown_dvt3 last)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LANE="${1:-all}"

DVT_TARGETS=(
    slc_facts
    slc_config
    slc_device_ports
    slc_firmware
    slc_managed_devices
    slc_network
    slc_system
    slc_users
    percepxion_facts
    percepxion_audit_logs
    percepxion_config
    percepxion_devices
    percepxion_firmware
    percepxion_import_devices
    percepxion_jobs
    percepxion_projects
    percepxion_smart_groups
    percepxion_telemetry
    percepxion_users
    percepxion_aoob_session
)

DVT3_TARGETS=(
    setup_dvt3
    slc_config_dvt3
    slc_managed_devices_dvt3
    slc_network_dvt3
    slc_system_dvt3
    slc_users_dvt3
    percepxion_firmware_dvt3
    percepxion_import_devices_dvt3
    percepxion_jobs_dvt3
    percepxion_projects_dvt3
    percepxion_users_dvt3
    percepxion_aoob_session_dvt3
    slc_device_ports_dvt3
    slc_users_dvt3
    percepxion_users_dvt3
    teardown_dvt3
)

PASS=()
FAIL=()
SKIP=()

run_target() {
    local target="$1"
    local tasks_file="${SCRIPT_DIR}/targets/${target}/tasks/main.yml"
    if [[ ! -f "${tasks_file}" ]]; then
        echo "=== SKIP: ${target} (no tasks/main.yml) ==="
        SKIP+=("${target}")
        return
    fi
    if bash "${SCRIPT_DIR}/run-target.sh" "${target}"; then
        PASS+=("${target}")
    else
        FAIL+=("${target}")
    fi
}

if [[ "${LANE}" == "dvt" || "${LANE}" == "all" ]]; then
    echo ""
    echo "=== DVT LANE (read-only) ==="
    for t in "${DVT_TARGETS[@]}"; do
        run_target "${t}"
    done
fi

if [[ "${LANE}" == "dvt3" || "${LANE}" == "all" ]]; then
    echo ""
    echo "=== DVT3 LANE (write) ==="
    for t in "${DVT3_TARGETS[@]}"; do
        run_target "${t}"
        if [[ "${t}" == "setup_dvt3" && " ${FAIL[*]} " == *" setup_dvt3 "* ]]; then
            echo "=== ABORT: setup_dvt3 failed, skipping remaining DVT3 targets ==="
            break
        fi
    done
fi

echo ""
echo "=== TEST SUMMARY ==="
echo "PASSED (${#PASS[@]}): ${PASS[*]:-none}"
echo "FAILED (${#FAIL[@]}): ${FAIL[*]:-none}"
echo "SKIPPED (${#SKIP[@]}): ${SKIP[*]:-none}"

[[ ${#FAIL[@]} -eq 0 ]]
