# Tool & Model Evaluations

Living record of what we evaluated and why it's in (or out of) the stack. New candidates
you hand over get appended here.

## Summary matrix

| Candidate | Type | Verdict | Role in ai-RedAlert |
|-----------|------|---------|---------------------|
| Metasploit Framework | Exploitation | ✅ Core | Primary exploitation engine (installed in image) |
| Nmap | Recon | ✅ Core | Enumeration; reference `ra-nmap` wrapper |
| hashcat | Cracking | ✅ Core | GPU hash cracking (needs GPU passthrough) |
| John the Ripper | Cracking | ✅ Core | CPU cracking, format coverage, `--rules` |
| Aircrack-ng + hcxtools | Wi-Fi | ✅ Core | WPA handshake capture → hashcat (needs adapter passthrough) |
| Hydra / Medusa | Cred attack | ✅ Core | Online dictionary attacks |
| Responder | Cred attack | ✅ Core | LLMNR/NBT-NS poisoning in the lab |
| netexec (nxc) | Recon/cred | ✅ Core | SMB/AD sweeping, the CrackMapExec successor |
| Anthropic-Cybersecurity-Skills | Skills/knowledge | ✅ Curated subset | Framework-tagged offensive workflows |
| BaronLLM-v2 (Q8, 14B) | LLM | ✅ Optional sidecar | `baron` profile advisor (not baked in) |

---

## Anthropic-Cybersecurity-Skills (`mukul975/...`)

**What it is.** ~818 markdown "skills" (YAML frontmatter + step-by-step workflow body),
agentskills.io-compatible, Apache-2.0, mapped to MITRE ATT&CK v19 / D3FEND / ATLAS and
NIST CSF 2.0. It is **knowledge scaffolding** — decision workflows a senior analyst would
follow — not exploit code or wordlists.

**Strengths.** Loads directly as Claude Code skills; framework tagging turns ad-hoc actions
into repeatable, reportable runbooks; explicit authorized-use mandate; very actively
maintained (~33k stars, 14 contributors).

**Weaknesses / cautions.** 818 skills is far more than a lab needs and heavily weighted to
defensive/SOC/threat-intel domains. Quality is community-reviewed, not formally verified —
treat any specific command as a starting point to validate, not gospel. Some skills assume
tooling we don't ship.

**Decision.** Vendor a **curated offensive subset** (recon, web-app, wifi, credential
access, exploitation, post-exploitation) under `skills/`, preserving upstream attribution
in `skills/NOTICE.md`; reference the full repo for everything else. See `skills/README.md`
for the pull process.

---

## BaronLLM-v2-OffensiveSecurityLLM-Q8 (`AlicanKiraz0/...`)

**What it is.** Qwen3-14B fine-tuned for offensive-security assistance, distributed as a
**Q8_0 GGUF (~15.7 GB)**. Runs locally via Ollama / llama.cpp / LM Studio. Author states
it was trained on curated security material *excluding raw exploit code*, with authorized-
use disclaimers and Apache-2.0 licensing (weights noted as requiring "separate
authorization" — we pull at runtime and never re-host).

**Strengths.** Genuinely useful **offline** advisor: explaining tool output, suggesting
enumeration paths, hash/service identification, report drafting. Local = no data leaves the
lab. Q8 preserves quality vs. lower quants.

**Weaknesses / cautions.**
- **Not "micro."** 14B Q8 needs ~16 GB+ RAM/VRAM and ~16 GB disk — it does *not* belong
  baked into a portable image. This is the one point where the brief's "micro LLM" and
  BaronLLM specifically pull in opposite directions.
- Capability claims (e.g. "13th globally," SecBench scores) are **self-reported and
  unverified**. Useful as an assistant; don't treat its output as authoritative — validate
  against primary sources and real tool behavior.
- Like any LLM it will hallucinate commands and flags. It advises; it never runs tools.

**Decision.** Ship it as an **optional Ollama sidecar** under the `baron` profile, pulled
at runtime. Offer a genuinely small `micro` profile (~3B, e.g. `qwen2.5:3b`) for
laptop-class portability, and `none` as the default. This satisfies both "incorporate
BaronLLM" and "keep it portable."

**Open item.** Confirm the exact redistribution terms of the weights before any packaging
that would re-host them (runtime pull avoids the issue).
