#!/usr/bin/env python3
"""
ai-RedAlert scope engine.

Single source of truth for "am I allowed to touch this target?". Every ra-* wrapper
calls check_target() before invoking a real tool. If the target is not covered by the
active scope allowlist, the tool does not run.

Scope file (scope/scope.yaml) format:

    engagement: home-lab-2026
    authorized_by: "self — personal lab, nodes I own"
    expires: 2026-12-31
    targets:
      - 10.10.10.0/24          # CIDR
      - 192.168.56.101         # single host
      - lab-dc01.local         # hostname (resolved + checked)
    exclude:
      - 10.10.10.1             # never touch the gateway
    ports: all                 # or a list like [22, 80, 443, 445]

Design notes:
  * Fail closed. No scope file, expired scope, or empty target list => nothing is in scope.
  * Excludes always win over includes.
  * Hostnames are resolved and every resolved IP must fall inside an authorized range.
"""
from __future__ import annotations

import ipaddress
import os
import socket
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

SCOPE_ENV = "REDALERT_SCOPE"
DEFAULT_SCOPE = "/opt/redalert/scope/scope.yaml"


class ScopeError(Exception):
    """Raised when scope cannot be loaded or a target is out of scope."""


def _scope_path() -> Path:
    return Path(os.environ.get(SCOPE_ENV, DEFAULT_SCOPE))


def load_scope(path: Path | None = None) -> dict:
    path = path or _scope_path()
    if not path.exists():
        raise ScopeError(
            f"No scope file at {path}. Copy scope/scope.example.yaml to scope/scope.yaml "
            f"and list ONLY your authorized lab targets."
        )
    if yaml is None:
        raise ScopeError("PyYAML not available in the image; cannot parse scope.")
    data = yaml.safe_load(path.read_text()) or {}
    if not data.get("targets"):
        raise ScopeError(f"Scope file {path} has no 'targets'. Fail closed: nothing is authorized.")

    expires = data.get("expires")
    if expires:
        exp = expires if isinstance(expires, date) else date.fromisoformat(str(expires))
        if date.today() > exp:
            raise ScopeError(
                f"Scope expired on {exp}. Re-authorize the engagement and update 'expires'."
            )
    return data


def _networks(entries: list[str]) -> list[ipaddress._BaseNetwork]:
    nets = []
    for e in entries or []:
        try:
            nets.append(ipaddress.ip_network(str(e), strict=False))
        except ValueError:
            pass  # hostnames handled separately
    return nets


def _resolve(host: str) -> list[str]:
    try:
        return list({info[4][0] for info in socket.getaddrinfo(host, None)})
    except socket.gaierror:
        return []


def _covered_by(net: ipaddress._BaseNetwork, ranges: list[ipaddress._BaseNetwork]) -> bool:
    return any(net == r or net.subnet_of(r) for r in ranges)


def excluded_hosts_in(target: str, scope: dict | None = None) -> list[str]:
    """Excluded addresses that fall inside `target` — hand these to the tool as --exclude."""
    scope = scope or load_scope()
    excludes = _networks(scope.get("exclude", []))
    try:
        net = ipaddress.ip_network(target, strict=False)
    except ValueError:
        return []
    out = []
    for x in excludes:
        try:
            if x.subnet_of(net) or x == net:
                out.append(str(x.network_address) if x.prefixlen in (32, 128) else str(x))
        except (TypeError, ValueError):
            pass
    return out


def check_target(target: str, scope: dict | None = None) -> bool:
    """Return True if `target` (IP, CIDR, or hostname) is in scope. Raise ScopeError otherwise.

    A range is authorized when it is covered by an authorized include and is not itself
    wholly an excluded range. Individual excluded hosts *inside* an authorized range do
    not block the range — wrappers pass them to the tool via excluded_hosts_in().
    """
    scope = scope or load_scope()
    includes = _networks(scope.get("targets", []))
    include_hosts = {str(t).lower() for t in scope.get("targets", [])}
    excludes = _networks(scope.get("exclude", []))
    exclude_hosts = {str(t).lower() for t in scope.get("exclude", [])}

    # Build the list of networks this target represents.
    try:
        nets = [ipaddress.ip_network(target, strict=False)]
    except ValueError:
        # hostname
        if target.lower() in exclude_hosts:
            raise ScopeError(f"'{target}' is explicitly excluded from scope.")
        if target.lower() in include_hosts:
            return True
        resolved = _resolve(target)
        if not resolved:
            raise ScopeError(f"Cannot resolve '{target}'; refusing (fail closed).")
        nets = [ipaddress.ip_network(r) for r in resolved]

    for net in nets:
        if _covered_by(net, excludes):
            raise ScopeError(f"{net} is an excluded range. Refusing.")
        if not _covered_by(net, includes):
            raise ScopeError(
                f"{net} (from '{target}') is NOT in the authorized scope. Refusing to run.\n"
                f"Add it to scope/scope.yaml only if you are authorized to test it."
            )
    return True


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: scope.py <target> [target ...]   |   scope.py --show", file=sys.stderr)
        return 2
    if argv[1] == "--show":
        try:
            s = load_scope()
        except ScopeError as e:
            print(f"✗ {e}", file=sys.stderr)
            return 1
        print(f"engagement : {s.get('engagement','<unnamed>')}")
        print(f"authorized : {s.get('authorized_by','<unspecified>')}")
        print(f"expires    : {s.get('expires','<none>')}")
        print(f"targets    : {', '.join(map(str, s.get('targets', [])))}")
        print(f"exclude    : {', '.join(map(str, s.get('exclude', []))) or '(none)'}")
        return 0

    rc = 0
    for t in argv[1:]:
        try:
            check_target(t)
            print(f"✓ {t} is IN scope")
        except ScopeError as e:
            print(f"✗ {t}: {e}", file=sys.stderr)
            rc = 1
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
