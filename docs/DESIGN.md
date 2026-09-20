# ai-RedAlert — Design

## Goals
1. **Simple** — a two-word workflow (`make build`, `make shell`) puts a full offensive
   toolset in front of you.
2. **Portable** — one Docker image, reproducible, runs anywhere Docker runs. No model
   blobs baked in.
3. **Effective** — the standard professional toolset (Metasploit, Nmap, hashcat, John,
   Aircrack-ng, Hydra, Responder, netexec) plus curated skills and an optional LLM advisor.
4. **Safe by construction** — scope enforcement and evidence capture are built into the
   plumbing, not bolted on.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│ host                                                      │
│                                                           │
│   make ── docker compose ─────────────┐                   │
│                                        ▼                   │
│   ┌───────────────────────┐   ┌──────────────────────┐    │
│   │ toolkit (Kali)        │   │ ollama sidecar        │    │
│   │                       │   │  (profile: micro/     │    │
│   │  bin/ra*  ── wrappers │◄──┤   baron; pulled at    │    │
│   │  lib/scope.py  guard  │HTTP│  runtime, opt-in)     │    │
│   │  lib/evidence.py      │   └──────────────────────┘    │
│   │  tools: nmap, msf,    │                                │
│   │   hashcat, aircrack…  │   volumes:                     │
│   └─────────┬─────────────┘    scope/  engagements/  skills/│
│             │                  (bind-mounted, persist)     │
└─────────────┼─────────────────────────────────────────────┘
              ▼
        authorized lab targets (isolated segment)
```

## Key decisions
See `docs/adr/` for the rationale. In short:
- **Kali rolling base** — the offensive toolset is one `apt-get` away and already packaged.
- **Ollama sidecar, not a baked-in model** — keeps the image lean and portable; the LLM is
  opt-in per host (`micro` ~3B for laptops, `baron` 14B for workstations, or none).
- **Curated skills subset** — vendor the offensive-relevant workflows; reference the rest.

## The scope guard (`lib/scope.py`)
Single source of truth for authorization. Fails closed on missing/expired scope or unlisted
targets. Ranges are authorized if covered by an include and not wholly excluded; excluded
hosts inside an authorized range are passed to the underlying tool as `--exclude` rather
than blocking the whole range. Wrappers call `check_target()` before executing anything.

## Evidence capture (`lib/evidence.py`)
Each engagement is a timestamped folder (`engagements/<date>_<name>/`) with `meta.yaml`
(scope snapshot + start time), `commands.log`, `scans/`, `loot/`, and `notes.md`. Wrappers
route raw output into `scans/` and log the invocation automatically, so a report is a
matter of assembling what's already captured.

## Wrapper pattern (`bin/ra-*`)
Every tool wrapper: (1) parses the target, (2) enforces scope, (3) injects excludes,
(4) routes output into the engagement, (5) logs the command, (6) `exec`s the real tool with
your arguments passed through. `bin/ra-nmap` is the reference implementation; adding
`ra-hydra`, `ra-hashcat`, etc. follows the same shape.

## Extending
- New tool wrapper → copy `bin/ra-nmap`, swap the final `exec`.
- New skill → drop a `SKILL.md` under `skills/` (see `skills/README.md`).
- New runbook → add to `docs/runbooks/`.
