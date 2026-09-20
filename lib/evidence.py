#!/usr/bin/env python3
"""
ai-RedAlert evidence capture.

An "engagement" is a timestamped folder under engagements/ that collects everything you
produce in a session: raw tool output, a command log, and notes. This is what you fold
into an OSCP/PNPT-style report. Keeping it structured from the first command means you
are never reconstructing what you did the night before a report is due.

Layout:
    engagements/2026-09-20_home-lab/
      ├─ meta.yaml          engagement name, scope snapshot, start time
      ├─ commands.log       every ra-* invocation, timestamped
      ├─ scans/             raw tool output (nmap.xml, etc.)
      ├─ loot/              creds, hashes, files pulled
      └─ notes.md           your running notes
"""
from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

ENGAGE_ENV = "REDALERT_ENGAGEMENT"
ROOT_ENV = "REDALERT_ENGAGEMENTS_DIR"
DEFAULT_ROOT = "/opt/redalert/engagements"


def root() -> Path:
    return Path(os.environ.get(ROOT_ENV, DEFAULT_ROOT))


def current() -> Path | None:
    name = os.environ.get(ENGAGE_ENV)
    if not name:
        return None
    p = root() / name
    return p if p.exists() else None


def new_engagement(name: str, scope_summary: str = "") -> Path:
    slug = f"{datetime.now():%Y-%m-%d}_{name}".replace(" ", "-")
    path = root() / slug
    for sub in ("scans", "loot"):
        (path / sub).mkdir(parents=True, exist_ok=True)
    meta = path / "meta.yaml"
    if not meta.exists():
        meta.write_text(
            f"engagement: {name}\n"
            f"started: {datetime.now().isoformat(timespec='seconds')}\n"
            f"scope: |\n"
            + "".join(f"  {line}\n" for line in scope_summary.splitlines())
        )
    notes = path / "notes.md"
    if not notes.exists():
        notes.write_text(f"# {name} — engagement notes\n\nStarted {datetime.now():%Y-%m-%d %H:%M}\n\n")
    return path


def log_command(argv: list[str]) -> None:
    eng = current()
    if not eng:
        return
    ts = datetime.now().isoformat(timespec="seconds")
    with (eng / "commands.log").open("a") as fh:
        fh.write(f"{ts}  {' '.join(argv)}\n")


def scan_path(filename: str) -> Path:
    eng = current()
    base = (eng / "scans") if eng else root()
    base.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%H%M%S")
    return base / f"{stamp}_{filename}"


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "new":
        p = new_engagement(sys.argv[2], " ".join(sys.argv[3:]))
        print(p)
    else:
        c = current()
        print(c if c else "(no active engagement — set REDALERT_ENGAGEMENT)")
