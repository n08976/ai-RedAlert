#!/usr/bin/env bash
# ai-RedAlert container entrypoint — banner, scope status, then hand off.
set -euo pipefail
RA_HOME="${REDALERT_HOME:-/opt/redalert}"

# Banner + scope status are for interactive sessions. Stay quiet for piped/helper
# invocations (make own, ra scope, scripted runs) so their output isn't buried.
if [ ! -t 0 ] || [ -n "${REDALERT_QUIET:-}" ]; then
  exec "$@"
fi

cat <<'BANNER'
   ___   _    ___         _   _  _         _
  / _ \ (_)  | _ \___ __| | | || |___ _ _| |_
 | (_) || |  |   / -_) _` | | __ / -_) '_|  _|
  \__,_||_|  |_|_\___\__,_| |_||_\___|_|  \__|   ai-RedAlert
BANNER
echo "  Authorized offensive-security lab toolkit — AUTHORIZED USE ONLY"
echo "  ---------------------------------------------------------------"

if python3 "$RA_HOME/lib/scope.py" --show >/tmp/scope 2>/tmp/scopeerr; then
  sed 's/^/  scope> /' /tmp/scope
else
  echo "  ⚠  No valid scope loaded:"
  sed 's/^/     /' /tmp/scopeerr
  echo "     Copy scope/scope.example.yaml -> scope/scope.yaml and add your lab targets."
  echo "     Tools will refuse to run until scope is set."
fi
echo "  ---------------------------------------------------------------"
echo "  ra help   → commands      ra tools → wrappers      ra new <name> → start"
echo

exec "$@"
