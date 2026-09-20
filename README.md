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

## Two ways to drive it

**Autonomous** — point it at anything and let it think like an operator. It enumerates,
runs the safe checks, and hands you a ranked attack plan:

```bash
ra new lab-box && export REDALERT_ENGAGEMENT=<slug>
ra auto 10.10.10.50            # IP, hostname, http://host/app, or a 10.10.10.0/24 range
ra auto 10.10.10.50 --exploit  # also run exploitation plays (deliberate)
ra auto 10.10.10.0/24 --full   # discover live hosts, all 65535 ports
```

`ra auto` runs recon + non-destructive vuln checks automatically and writes an
`attackplan_<host>.md` (open services → exact commands → MITRE technique → matching
playbook, plus an LLM-synthesised plan if a model is up). Actual exploitation stays behind
`--exploit`.

**Explicit** — tell it exactly what to do:

```bash
ra run 10.10.10.50 --only web,smb     # only these service categories
ra-nmap -sC -sV 10.10.10.50           # or drive any tool directly (scope-enforced)
ra-hydra -L users.txt -P rockyou.txt ssh://10.10.10.50
```

> **Note:** engagement files are root-owned on the host (the tools need root inside the
> container). Run `make own` to reclaim ownership of `engagements/`.

Everything captured during a session lands in `engagements/<date>-<name>/` — scans,
loot, notes, and a timeline you can fold straight into a report.

---

## Command reference

### `make` (host — the outer UX)
| Command | What it does |
|---------|--------------|
| `make build` | Build the toolkit image (Kali + offensive toolset) |
| `make shell` | Drop into the scope-aware toolkit shell |
| `make scope` | Show the active scope allowlist |
| `make llm-micro` | Start the LLM sidecar + pull the small ~3B model (laptop) |
| `make llm-baron` | Start the LLM sidecar + pull BaronLLM-v2 14B (workstation, 16GB+ RAM) |
| `make llm-down` | Stop the LLM sidecar (model stays cached) |
| `make gpu-check` | Verify the host GPU is visible to Docker |
| `make own` | Reclaim host ownership of root-owned `engagements/` files |
| `make test` | Run the scope-engine self-tests (no container needed) |
| `make down` / `make clean` | Tear down the stack / remove the image |
| `GPU=1 make shell` | Any target with GPU acceleration (needs nvidia-container-toolkit) |

### `ra` (inside the toolkit — the control CLI)
| Command | What it does |
|---------|--------------|
| `ra new <name>` | Start an engagement (timestamped evidence folder) |
| `ra use <slug>` | Print the `export` line to switch the active engagement |
| `ra list` | List engagements |
| `ra scope` | Show the active scope allowlist |
| `ra check <target…>` | Test whether target(s) are in scope |
| `ra tools` | List the `ra-*` tool wrappers |
| `ra auto <target> [flags]` | **Autonomous** assessment (see flags below) |
| `ra run <target> --only <cats>` | **Explicit** mode: run chosen service categories |

### `ra auto` flags
| Flag | Effect |
|------|--------|
| *(none)* | Enumerate → run safe `enum`/`vuln` plays → write ranked `attackplan_<host>.md` |
| `--full` | Scan all 65535 ports (slower) |
| `--exploit` | Also run exploitation plays (deliberate — can crash lab services) |
| `--no-act` | Plan only; run nothing |
| `--no-llm` | Skip the LLM synthesis step |
| `--only <cats>` | Restrict to categories: `web,smb,ssh,ftp,snmp,ldap,db,rdp,vnc` |

Target can be an **IP**, **hostname**, **URL** (`http://host/app`), or **CIDR** (`10.10.10.0/24`).

### `ra-*` tool wrappers (scope-enforced, evidence-captured)
| Wrapper | Wraps | Example |
|---------|-------|---------|
| `ra-nmap` | nmap | `ra-nmap -sC -sV 10.10.10.50` |
| `ra-hydra` | hydra (online dictionary) | `ra-hydra -L users.txt -P rockyou.txt ssh://10.10.10.50` |
| `ra-hashcat` | hashcat (offline, GPU-aware) | `ra-hashcat -m 22000 hs.hc22000 rockyou.txt` |
| `ra-john` | John the Ripper | `ra-john --format=nt hashes.txt --wordlist=rockyou.txt` |
| `ra-msf` | Metasploit (DB + logging) | `ra-msf` |
| `ra-wifi` | handshake capture/convert | `ra-wifi capture --bssid AA:BB:… --channel 6 --iface wlan0mon` |
| `ra-ai` | local LLM advisor | `ra-ai "identify this hash: $H"` |

### Typical session
```bash
make build                                   # once
cp scope/scope.example.yaml scope/scope.yaml # list ONLY your lab targets
make shell
ra new lab-box && export REDALERT_ENGAGEMENT=<slug>   # (ra new prints the exact line)
ra auto 10.10.10.50                          # or: ra run 10.10.10.50 --only web,smb
# results + attack plan in engagements/<slug>/ ; run `make own` on the host to read them
```

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
