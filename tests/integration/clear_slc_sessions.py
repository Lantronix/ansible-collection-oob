#!/usr/bin/env python3
"""Clear all REST API sessions on an SLC9000 via SSH admin web restart.

Reads credentials from tests/integration/integration_config.yml (gitignored).
Usage:
    python3 clear_slc_sessions.py           # clears write-lane host
    python3 clear_slc_sessions.py --read    # clears read-lane host
    python3 clear_slc_sessions.py --both    # clears both lanes
"""
from __future__ import absolute_import, division, print_function

import argparse
import os
import sys
import time

try:
    import paramiko
except ImportError:
    sys.exit("paramiko is required: pip install paramiko")

try:
    import yaml
except ImportError:
    # Fall back to a minimal key=value parser for simple YAML
    yaml = None


def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "integration_config.yml")
    if not os.path.exists(config_path):
        sys.exit("integration_config.yml not found at: " + config_path)
    cfg = {}
    with open(config_path) as f:
        if yaml:
            cfg = yaml.safe_load(f) or {}
        else:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if ":" in line:
                    k, _sep, v = line.partition(":")
                    cfg[k.strip()] = v.strip().strip('"')
    return cfg


def restart_web(host, username, password, label):
    print("Clearing REST sessions on {} ({})...".format(label, host))
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=username, password=password, timeout=15)
    except Exception as exc:
        print("SSH connect failed for {}: {}".format(label, exc))
        return False

    channel = client.invoke_shell()
    time.sleep(1)
    channel.recv(4096)

    channel.send("admin web restart\n")
    time.sleep(2)
    out = channel.recv(4096).decode(errors="replace")

    if "Are you sure" in out or "[no]" in out:
        channel.send("yes\n")
        time.sleep(3)
        out += channel.recv(4096).decode(errors="replace")

    client.close()

    if "restarted" in out.lower():
        print("  OK: web server restarted on {}".format(label))
        return True
    else:
        print("  WARNING: unexpected response from {}: {}".format(label, out[-200:]))
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--read", action="store_true", help="Clear read-lane sessions")
    parser.add_argument("--both", action="store_true", help="Clear both lanes")
    args = parser.parse_args()

    cfg = load_config()

    ok = True
    if args.both or (not args.read):
        ok &= restart_web(
            cfg.get("slc_write_host", ""),
            cfg.get("slc_write_username", "sysadmin"),
            cfg.get("slc_write_password", ""),
            "write-lane",
        )

    if args.read or args.both:
        ok &= restart_web(
            cfg.get("slc_read_host", ""),
            cfg.get("slc_read_username", "sysadmin"),
            cfg.get("slc_read_password", ""),
            "read-lane",
        )

    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
