#!/usr/bin/env bash
# Run all integration targets in the standard DVT → write sequence.
# Usage: bash tests/integration/run-all.sh [dvt|write|all]
# Default: all
#
# DVT lane   - read-only targets against slc9000 and percepxion-primary
# Write lane - write targets against slc9000-write and percepxion-write
#              (runs setup_write_lane first, teardown_write_lane last)

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

WRITE_TARGETS=(
    setup_write_lane
    slc_config_write
    slc_managed_devices_write
    slc_network_write
    slc_system_write
    slc_users_write
    slc_device_ports_write
    percepxion_firmware_write
    percepxion_import_devices_write
    percepxion_jobs_write
    percepxion_projects_write
    percepxion_users_write
    percepxion_aoob_session_write
    teardown_write_lane
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

if [[ "${LANE}" == "write" || "${LANE}" == "all" ]]; then
    echo ""
    echo "=== WRITE LANE ==="
    for t in "${WRITE_TARGETS[@]}"; do
        run_target "${t}"
        if [[ "${t}" == "setup_write_lane" && " ${FAIL[*]} " == *" setup_write_lane "* ]]; then
            echo "=== ABORT: setup_write_lane failed, skipping remaining write targets ==="
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
