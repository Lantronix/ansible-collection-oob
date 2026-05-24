#!/usr/bin/env bash
# Run a single integration target against real lab devices.
# Usage: bash tests/integration/run-target.sh <target_name>
# Example: bash tests/integration/run-target.sh slc_facts
#
# Requires integration_config.yml to be present (gitignored, local credentials).
# Generates a static inventory at /tmp/oob-lab-inventory before each run.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COLLECTION_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
TARGET="${1:-}"

if [[ -z "${TARGET}" ]]; then
    echo "Usage: $0 <target_name>"
    echo "Available targets:"
    ls "${SCRIPT_DIR}/targets/"
    exit 1
fi

TASKS_FILE="${SCRIPT_DIR}/targets/${TARGET}/tasks/main.yml"
if [[ ! -f "${TASKS_FILE}" ]]; then
    echo "ERROR: Target not found: ${TARGET}"
    echo "Expected tasks file: ${TASKS_FILE}"
    exit 1
fi

CONFIG_FILE="${SCRIPT_DIR}/integration_config.yml"
if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "ERROR: integration_config.yml not found."
    echo "Copy integration_config.yml.template to integration_config.yml and fill in credentials."
    exit 1
fi

INVENTORY="/tmp/oob-lab-inventory"
python3 "${SCRIPT_DIR}/gen_inventory.py" "${INVENTORY}"

PLAYBOOK="/tmp/oob-run-${TARGET}.yml"
cat > "${PLAYBOOK}" << PLAYBOOK_EOF
---
- hosts: localhost
  gather_facts: false
  vars_files:
    - ${CONFIG_FILE}
  collections:
    - lantronix.oob
  tasks:
    - name: "Run integration target: ${TARGET}"
      import_tasks: ${TASKS_FILE}
PLAYBOOK_EOF

echo "=== Running target: ${TARGET} ==="
ANSIBLE_COLLECTIONS_PATH="${COLLECTION_ROOT}/../.." \
    ansible-playbook -i "${INVENTORY}" -i localhost, "${PLAYBOOK}" -v
EXIT_CODE=$?

rm -f "${PLAYBOOK}"

if [[ ${EXIT_CODE} -eq 0 ]]; then
    echo "=== PASSED: ${TARGET} ==="
else
    echo "=== FAILED: ${TARGET} (exit ${EXIT_CODE}) ==="
fi

exit ${EXIT_CODE}
