# Contributing to lantronix.oob

Thank you for your interest in contributing to the `lantronix.oob` Ansible collection.

## Before You Start

- Open an issue before submitting a PR for significant changes. This lets us discuss the approach before you invest time in an implementation.
- For bug fixes and small documentation improvements, a PR without a prior issue is fine.

## Development Setup

`ansible-test` requires the collection to be checked out at a specific path:

```bash
mkdir -p ansible_collections/lantronix
git clone https://github.com/lantronix/ansible-collection-oob ansible_collections/lantronix/oob
cd ansible_collections/lantronix/oob
pip install requests
```

## Running Tests

All commands run from `ansible_collections/lantronix/oob/`.

```bash
# Sanity tests (must be 0 errors before merge)
ansible-test sanity --python 3.11

# Unit tests
ansible-test units --python 3.11

# Integration tests (requires lab device access — see below)
ansible-test integration --python 3.11
```

## Integration Tests

Integration tests require network access to a live SLC 9000 and a Percepxion instance.

1. Copy `tests/integration/integration_config.yml.template` to `tests/integration/integration_config.yml`.
2. Fill in your device credentials.
3. Run `ansible-test integration --python 3.11`.

`integration_config.yml` is gitignored and must never be committed.

## Code Standards

Every module must pass `ansible-test sanity` before merge. Key requirements:

- All Python files need `from __future__ import absolute_import, division, print_function` and `__metaclass__ = type`.
- Module files need `#!/usr/bin/python` and `# -*- coding: utf-8 -*-` as the first two lines.
- `DOCUMENTATION`, `EXAMPLES`, and `RETURN` docstrings must appear before any imports.
- Passwords and secrets must have `no_log=True` in `argument_spec`.
- All write operations must implement idempotency: fetch current state, compare, write only if changed.
- `check_mode` must skip writes (`supports_check_mode=True` + `if not module.check_mode`).
- Error handling: no bare `except:`, no `sys.exit()`. All errors route to `module.fail_json()`.

## Commit Convention

```
feat: add slc_firmware module
fix: correct idempotency in percepxion_users when role changes
test: add integration target for slc_system
docs: add EXAMPLES for percepxion_config module
```

## License

By contributing, you agree that your contributions will be licensed under the Apache 2.0 License.
