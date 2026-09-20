# 🔴 ai-RedAlert

**A portable, containerized offensive-security lab toolkit for authorized testing, cert prep, and research.**

ai-RedAlert bundles the standard offensive toolset (Metasploit, Nmap, hashcat, John,
Aircrack-ng, Hydra, Responder, and more) into one reproducible Docker image, wraps them
in a **scope-enforcement layer** so you stay inside your lab, captures **structured
evidence** for each engagement, and — optionally — ships a local **offensive-security
LLM advisor** as a pull-on-demand sidecar. It is built for practitioners studying for
OSCP / PNPT / CPTS-style certifications who want a repeatable, offline, portable rig.

---

## ⚠️ Authorized use only

This toolkit is for testing systems **you own** or have **explicit written permission**
to assess. Every wrapped tool checks a target against your **scope allowlist** before it
runs; running out of scope is on you. Read **[docs/RULES-OF-ENGAGEMENT.md](docs/RULES-OF-ENGAGEMENT.md)**
before your first run. Unauthorized access to computer systems is a crime in virtually
every jurisdiction. Don't.

---

## Quickstart

```bash
# 1. Build the image (Kali rolling + full offensive toolset)
make build

# 2. Define your lab's authorized targets
cp scope/scope.example.yaml scope/scope.yaml
$EDITOR scope/scope.yaml            # add ONLY your lab nodes / CIDRs

# 3. Drop into the toolkit shell (scope-aware, evidence auto-captured)
make shell

# 4. (optional) Bring up the local LLM advisor
make llm-micro      # ~3B model, laptop-friendly
# or
make llm-baron      # BaronLLM-v2 14B, workstation (16GB+ RAM)
```

Everything captured during a session lands in `engagements/<date>-<name>/` — scans,
loot, notes, and a timeline you can fold straight into a report.

---

## What's inside

| Layer | What it gives you |
|-------|-------------------|
| **Toolkit image** | Kali rolling base with recon, exploitation, wifi, and cracking tools pre-installed |
| **Scope guard** (`lib/`, `bin/ra-scope`) | Allowlist check enforced by every `ra-*` wrapper — refuses out-of-scope targets |
| **Evidence capture** | Per-engagement folders, command logging, timestamped artifacts |
| **Skills** (`skills/`) | Curated offensive workflows (recon/web/wifi/cred-access/exploitation) from the Anthropic-Cybersecurity-Skills project, framework-tagged (MITRE ATT&CK) |
| **LLM advisor** (`llm/`) | Optional Ollama sidecar; `micro`, `baron`, or `none` profiles, pulled at runtime |
| **Docs** (`docs/`) | Design, tool evaluations, runbooks, rules of engagement |

See **[docs/DESIGN.md](docs/DESIGN.md)** for the architecture and **[docs/TOOL-EVALUATIONS.md](docs/TOOL-EVALUATIONS.md)**
for the tool/model assessments driving these choices.

---

## Tool categories

- **Recon / enumeration** — Nmap, masscan, enum4linux-ng, netexec, gobuster, nikto
- **Exploitation** — Metasploit Framework, searchsploit
- **Credential attacks** — Hydra, Medusa (dictionary/online), Responder (LLMNR/NBT-NS)
- **Hash / password cracking** — hashcat (GPU), John the Ripper
- **Wi-Fi** — Aircrack-ng suite, hcxtools/hcxdumptool (WPA handshake → hashcat)

Wi-Fi and GPU cracking need host hardware passthrough — see
**[docs/runbooks/](docs/runbooks/)** for adapter and GPU setup.

---

## Repository layout

```
ai-RedAlert/
├─ docker/        Dockerfile, compose, entrypoint
├─ bin/           ra-* scope-aware tool wrappers + CLI
├─ lib/           scope engine, evidence capture, shared helpers
├─ scope/         authorized-target allowlist (yours stays out of git)
├─ skills/        curated offensive skills (vendored subset)
├─ engagements/   captured results (git-ignored)
├─ llm/           optional Ollama sidecar + model profiles
└─ docs/          design, tool evals, runbooks, RoE, ADRs
```

## License

Apache-2.0. Vendored third-party skills retain their upstream licensing and attribution —
see `skills/NOTICE.md`.
