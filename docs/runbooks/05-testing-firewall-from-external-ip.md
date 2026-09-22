# Runbook 05 — Testing your firewall from an external IP (VPN egress)

**Goal:** scan your **own** public-facing host from an external source IP (a VPN exit in
another location) to see what your firewall actually exposes to the outside world — and
verify egress/ingress rules from alternate geographies.

> Only your own public IP / infrastructure. This routes real traffic across the internet;
> scanning anything you don't own is illegal. `ra auto`/`ra-nmap` **fail closed** here — no
> scan runs unless the VPN tunnel is confirmed up.

## How it works
A [gluetun](https://github.com/qdm12/gluetun) sidecar (Surfshark/Nord) owns a network
namespace with a **kill-switch firewall**. The toolkit rides that namespace
(`network_mode: service:gluetun`), so every tool egresses through the VPN. If the tunnel
drops, gluetun blocks all traffic and `lib/vpn.py` refuses to run — your real IP can't leak.

## 0. One-time: credentials
```bash
cp .env.vpn.example .env.vpn
$EDITOR .env.vpn
```
Fill in **service credentials** (not your account login):
- Surfshark: *Account → VPN → Manual setup → Credentials*
- Pick `SERVER_COUNTRIES` for the exit location you want to appear to come from.

## 1. Bring up the VPN and confirm the exit IP
```bash
make vpn-up        # starts gluetun, waits for the tunnel, prints the external exit IP
make vpn-status    # re-check any time
```
`make vpn-up` aborts if it can't confirm an exit IP — that's the leak guard.

## 2. Scope your own public IP and scan
```bash
# scope.yaml -> targets: [ <your.public.ip>/32 ]
make shell-vpn                      # toolkit shell routed through the VPN
ra new fw-external && export REDALERT_ENGAGEMENT=<slug>
ra vpn                              # banner also shows the active exit IP
ra auto <your.public.ip>           # enumerate what the internet can see
```
Compare the result to what you *think* the firewall allows. Anything `ra auto` finds open
from an external IP is reachable from the internet.
`(MITRE ATT&CK: T1595 — Active Scanning, from an external vantage point)`

## 3. Test from multiple locations
Change `SERVER_COUNTRIES` in `.env.vpn`, `make vpn-down && make vpn-up`, and re-scan — this
checks geo-based firewall rules and whether exposure differs by source region.

## 4. Tear down
```bash
make vpn-down
```

## Notes / by design
- **No local LLM in VPN mode** — the toolkit is in gluetun's netns and can't reach the
  `ollama` sidecar. Run `ra auto --no-llm` (it degrades automatically) or generate the LLM
  plan separately in normal mode.
- **NET_RAW only** in VPN mode (no NET_ADMIN) so tools can't weaken the kill-switch.
- **Wi-Fi / LAN tools are out of scope here** — those need local-segment access, not VPN
  egress.

## Deliverable
`engagements/<slug>/` with the external-vantage scan and the exit IP recorded — evidence of
exactly what your firewall exposes to the outside world.
