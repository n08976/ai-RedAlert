# ai-RedAlert — notes for AI assistants

Portable, containerized **offensive-security lab toolkit** for **authorized** testing and
certification prep (OSCP/PNPT/CPTS-style). Owner: n08976. Treat all work as authorized-lab
scoped — this is the operator's own lab and test nodes.

## What this is
- Kali-rolling Docker image with the standard offensive toolset (Metasploit, Nmap, hashcat,
  John, Aircrack-ng, Hydra, Responder, netexec).
- A **scope guard** (`lib/scope.py`) every `ra-*` wrapper calls before running — fails
  closed on unlisted/expired targets.
- **Evidence capture** (`lib/evidence.py`) — timestamped engagement folders.
- Optional **Ollama LLM sidecar** (`micro`/`baron` profiles, pulled at runtime).
- Curated **skills** vendored from Anthropic-Cybersecurity-Skills.

## Conventions
- New tool wrapper → copy `bin/ra-nmap` (enforce scope → inject excludes → route output →
  log → exec). Keep the target as the last positional arg.
- Never bake models into the image; never commit `engagements/` contents or `scope/scope.yaml`.
- Run `python3 tests/test_scope.py` after touching `lib/scope.py`.
- Docs: design in `docs/DESIGN.md`, decisions in `docs/adr/`, tool assessments in
  `docs/TOOL-EVALUATIONS.md`, runbooks in `docs/runbooks/`, safety in
  `docs/RULES-OF-ENGAGEMENT.md`.

## UX
`make build` → `make shell` → `ra new <name>` → work. `make llm-micro|llm-baron` for the
advisor. `make help` lists everything.
