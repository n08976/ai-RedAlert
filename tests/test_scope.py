#!/usr/bin/env python3
"""Self-tests for the ai-RedAlert scope engine. Run: python3 tests/test_scope.py"""
import os, sys, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
import scope  # noqa: E402

SCOPE = """
engagement: test-lab
authorized_by: self
expires: 2999-01-01
targets: [10.10.10.0/24, 192.168.56.101, lab.example]
exclude: [10.10.10.1]
"""

def run():
    sf = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    sf.write(SCOPE); sf.close()
    os.environ["REDALERT_SCOPE"] = sf.name
    cases = [
        ("10.10.10.50", True), ("192.168.56.101", True), ("10.10.10.0/24", True),
        ("10.10.10.1", False), ("8.8.8.8", False), ("192.168.56.102", False),
        ("10.10.0.0/16", False),
    ]
    failures = 0
    for tgt, expect in cases:
        try:
            scope.check_target(tgt); got = True
        except scope.ScopeError:
            got = False
        ok = got == expect
        failures += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {tgt:16} expect={'IN' if expect else 'OUT'}")
    # exclude passthrough
    exc = scope.excluded_hosts_in("10.10.10.0/24")
    assert exc == ["10.10.10.1"], f"unexpected excludes: {exc}"
    print(f"[PASS] excluded_hosts_in('10.10.10.0/24') == {exc}")
    # expired scope fails closed
    from pathlib import Path
    ef = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    ef.write(SCOPE.replace("2999-01-01", "2000-01-01")); ef.close()
    try:
        scope.load_scope(Path(ef.name))
        print("[FAIL] expired scope was accepted"); failures += 1
    except scope.ScopeError:
        print("[PASS] expired scope fails closed")
    os.unlink(sf.name); os.unlink(ef.name)
    # wifi allowlist
    wf = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    wf.write(SCOPE + "\nwifi:\n  bssids: ['AA:BB:CC:DD:EE:FF']\n  essids: ['my-lab-ap']\n")
    wf.close()
    from pathlib import Path as _P
    wsc = scope.load_scope(_P(wf.name))
    try:
        scope.check_wifi("aa:bb:cc:dd:ee:ff", None, wsc); print("[PASS] wifi bssid (case-insensitive) authorized")
    except scope.ScopeError: print("[FAIL] wifi bssid should be authorized"); failures += 1
    try:
        scope.check_wifi("11:22:33:44:55:66", "rogue", wsc); print("[FAIL] rogue AP accepted"); failures += 1
    except scope.ScopeError: print("[PASS] unauthorized AP refused")
    os.unlink(wf.name)
    print("\n" + ("ALL PASS" if failures == 0 else f"{failures} FAILURE(S)"))
    return 1 if failures else 0

if __name__ == "__main__":
    raise SystemExit(run())
