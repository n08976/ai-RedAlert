# ADR 0001 — Foundational architecture

- **Status:** Accepted
- **Date:** 2026-09-20

## Context
Building a portable, simple, effective offensive-security lab toolkit for authorized
testing and certification prep. Three foundational choices were decided with the operator.

## Decisions

### 1. Container base: Kali Linux rolling
The offensive toolset (Metasploit, Nmap, aircrack-ng, hashcat, John, Hydra, Responder,
netexec) is already packaged and maintained in Kali. Alternative (slim Debian + hand-built
tools) was rejected as more maintenance for little portability gain. We install a **curated
package set** rather than the full `kali-linux-headless` metapackage to control image size.

### 2. LLM: pluggable Ollama sidecar, not a baked-in model
BaronLLM-v2 (14B, 15.7 GB) directly conflicts with the portability goal if embedded. We run
the LLM as an **optional Ollama sidecar** with runtime-pulled profiles: `micro` (~3B,
laptop), `baron` (14B, workstation), or none (default). Keeps the image lean; capability is
opt-in per host. Models are never committed or baked in.

### 3. Skills: curated offensive subset, vendored + referenced
The upstream Anthropic-Cybersecurity-Skills repo has ~818 skills, mostly defensive. We
vendor the offensive-relevant domains and reference the rest, preserving upstream
attribution and Apache-2.0 licensing.

## Consequences
- Image is larger than a minimal Debian build but dramatically simpler to maintain.
- LLM users need a one-time `make llm-*` to pull a model; base users pay nothing for it.
- Wi-Fi and GPU cracking require host hardware passthrough (documented in runbooks/compose).
- Cross-cutting safety (scope guard, evidence capture) is implemented once in `lib/` and
  reused by all wrappers.
