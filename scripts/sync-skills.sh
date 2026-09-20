#!/usr/bin/env bash
# sync-skills.sh — refresh the curated offensive skill subset from upstream.
#
# Clones mukul975/Anthropic-Cybersecurity-Skills into a temp dir and copies only the
# offensive-lab-relevant domains into skills/. Deliberate copy (not a submodule) so the
# vendored set stays small and auditable. Re-run to update.
set -euo pipefail
RA_HOME="${REDALERT_HOME:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
UPSTREAM="https://github.com/mukul975/Anthropic-Cybersecurity-Skills.git"
# Domains we keep. Upstream skill folder names vary; we match by keyword.
KEEP='recon|enumerat|discovery|web-app|web_app|webapp|wifi|wireless|password|credential|hash|brute|exploit|post-exploit|lateral|privilege'

tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
echo "[sync-skills] cloning upstream (shallow)…"
git clone --depth 1 "$UPSTREAM" "$tmp/upstream" >/dev/null 2>&1
src="$tmp/upstream/skills"; [ -d "$src" ] || { echo "upstream layout changed: no skills/ dir" >&2; exit 1; }

count=0
while IFS= read -r skill; do
  name="$(basename "$skill")"
  if echo "$name" | grep -qiE "$KEEP"; then
    dest="$RA_HOME/skills/$name"
    rm -rf "$dest"; cp -r "$skill" "$dest"; count=$((count+1))
  fi
done < <(find "$src" -mindepth 1 -maxdepth 1 -type d)

echo "[sync-skills] copied $count offensive skills into skills/"
echo "[sync-skills] review and commit. Upstream attribution: skills/NOTICE.md"
