#!/usr/bin/env python3
"""
ai-RedAlert VPN gate.

When the toolkit runs in VPN mode (docker/docker-compose.vpn.yml) it shares the gluetun
sidecar's network namespace, so ALL traffic egresses through the VPN with gluetun's
kill-switch firewall. This module is the fail-closed guard: if RA_VPN_REQUIRED is set,
no scan runs unless the tunnel is confirmed up and a real exit IP is reachable.

Design (reviewed with pal / gpt-5.2):
  * tunnel_up(): a tun*/wg* interface exists AND the default route goes via it.
  * exit_ip(): only called once tunnel_up() is true; tries several echo endpoints so a
    single flaky provider doesn't cause a false "down".
  * require_vpn(): raises VpnError (fail closed) when VPN is required but not confirmed.
"""
from __future__ import annotations

import os
import subprocess
from urllib.request import urlopen

REQUIRE_ENV = "RA_VPN_REQUIRED"
IP_ENDPOINTS = ["https://api.ipify.org", "https://ifconfig.me/ip", "https://icanhazip.com"]


class VpnError(Exception):
    pass


def _sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return ""


def vpn_interface() -> str | None:
    """Name of the active VPN interface (tun0 / wg0 / …) that carries the default route."""
    route = _sh(["ip", "route", "show", "default"])
    for token in route.split():
        if token.startswith(("tun", "wg")):
            return token
    # default route didn't name a tun/wg dev
    return None


def tunnel_up() -> bool:
    """True only when the default route egresses via a tun*/wg* interface that has an address."""
    dev = vpn_interface()
    if not dev:
        return False
    if f"dev {dev}" not in _sh(["ip", "route", "show", "default"]):
        return False
    return bool(_sh(["ip", "-o", "addr", "show", "dev", dev]).strip())


def exit_ip(timeout: int = 6) -> str | None:
    """Public IP as seen from this netns. Gated behind tunnel_up() so it can't 'succeed in
    the clear'. Tries several endpoints; returns the first that answers."""
    if not tunnel_up():
        return None
    for url in IP_ENDPOINTS:
        try:
            ip = urlopen(url, timeout=timeout).read().decode().strip()
            if ip and len(ip) <= 45:
                return ip
        except Exception:
            continue
    return None


def required() -> bool:
    return os.environ.get(REQUIRE_ENV, "").strip() not in ("", "0", "false", "no")


def status() -> dict:
    dev = vpn_interface()
    return {"required": required(), "interface": dev, "tunnel_up": tunnel_up(),
            "exit_ip": exit_ip() if dev else None}


def require_vpn() -> None:
    """Fail closed if VPN is required but not confirmed. No-op when not required."""
    if not required():
        return
    if not tunnel_up():
        raise VpnError(
            "RA_VPN_REQUIRED is set but no VPN tunnel is up (no default route via tun*/wg*).\n"
            "Bring the VPN up first:  make vpn-up   (or exit VPN mode).\n"
            "Refusing to run — this prevents traffic leaving from your real IP."
        )
    ip = exit_ip()
    if not ip:
        raise VpnError(
            "VPN interface is up but no external exit IP could be confirmed. Refusing to run "
            "(fail closed) rather than risk originating traffic outside the tunnel."
        )


if __name__ == "__main__":
    import json, sys
    if len(sys.argv) > 1 and sys.argv[1] == "require":
        try:
            require_vpn(); print("✓ VPN gate passed" if required() else "· VPN not required")
        except VpnError as e:
            print(f"✗ {e}", file=sys.stderr); raise SystemExit(3)
    else:
        print(json.dumps(status(), indent=2))
