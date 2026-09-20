#!/usr/bin/env bash
# sync-skills.sh — refresh the curated offensive skill subset from upstream.
#
# Shallow-clones mukul975/Anthropic-Cybersecurity-Skills and runs select_skills.py, which
# classifies skills by their frontmatter tags/subdomain and vendors only the offensive
# lab-relevant ones into skills/<bucket>/, regenerating skills/INDEX.md. Re-run to update.
set -euo pipefail
RA_HOME="${REDALERT_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
UPSTREAM="https://github.com/mukul975/Anthropic-Cybersecurity-Skills.git"
tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
echo "[sync-skills] cloning upstream (shallow)…"
git clone --depth 1 "$UPSTREAM" "$tmp/up" >/dev/null 2>&1
[ -d "$tmp/up/skills" ] || { echo "upstream layout changed: no skills/ dir" >&2; exit 1; }
cd "$RA_HOME"
python3 scripts/select_skills.py "$tmp/up"
echo "[sync-skills] done. Review 'git status' and commit. Attribution: skills/NOTICE.md"
