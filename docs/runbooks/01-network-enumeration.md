# Runbook 01 — Network enumeration

**Goal:** go from "I have a lab subnet" to "I know what's alive, what services run, and
where to focus," with everything captured for the report.

> Authorized lab targets only. `ra-*` tools refuse anything outside `scope/scope.yaml`.

## 0. Set up the engagement
```bash
make shell                         # inside the toolkit container
ra scope                           # confirm the allowlist is what you expect
ra new lab-sweep                   # create the evidence folder
export REDALERT_ENGAGEMENT=<slug>  # the command above prints the exact line
```

## 1. Host discovery
```bash
ra-nmap -sn 10.10.10.0/24          # ping sweep; excluded hosts auto-skipped
```
Output lands in `engagements/<slug>/scans/`. Note the live hosts.

## 2. Service / version enumeration
```bash
ra-nmap -sC -sV -O 10.10.10.50     # default scripts + versions + OS guess
ra-nmap -p- --min-rate 2000 10.10.10.50   # full TCP port sweep, then re-scan interesting ports
```
`(MITRE ATT&CK: T1046 — Network Service Discovery)`

## 3. SMB / AD sweep (Windows-heavy labs)
```bash
netexec smb 10.10.10.0/24                     # null-session sweep, signing, OS
enum4linux-ng -A 10.10.10.50                  # users, shares, policy
```

## 4. Web surface
```bash
ra-nmap -p80,443,8080 --script http-title 10.10.10.50
gobuster dir -u http://10.10.10.50 -w /usr/share/wordlists/dirb/common.txt
```

## 5. Triage & next steps
Review `scans/`, jot findings in `notes.md`. Feed context to the advisor if the sidecar is
up:
```bash
ra-ai "given these open ports and versions, what are the highest-value next steps?" < scans/<file>.nmap
```
Then move to exploitation (Metasploit / searchsploit) against the services you prioritized —
covered in a later runbook.

## Deliverable
`engagements/<slug>/` now holds: `meta.yaml`, `commands.log`, raw scans, and `notes.md` —
the raw material for the enumeration section of your report.
