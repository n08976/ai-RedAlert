# LLM advisor (optional)

ai-RedAlert can run a **local, offline** LLM as an advisor — explaining tool output,
suggesting enumeration paths, identifying hash/service types, and drafting report language.
It runs as an **Ollama sidecar** container and is entirely optional. Nothing is baked into
the toolkit image; models are pulled at runtime, so the base stays portable.

## Profiles

| Profile | Model | Size | Host needs | Use when |
|---------|-------|------|-----------|----------|
| `micro` | `qwen2.5:3b` (default) | ~2 GB | any laptop | portable, quick advice |
| `baron` | BaronLLM-v2 Q8 (14B) | ~15.7 GB | 16 GB+ RAM / a GPU | deepest offensive-sec help |
| none | — | — | — | default; no LLM |

Override the models via env: `MICRO_MODEL=...`, `BARON_MODEL=...` (see `Makefile`).

## Start / stop
```bash
make llm-micro      # start sidecar + pull the small model
make llm-baron      # start sidecar + pull BaronLLM (large; first pull is slow)
make llm-down       # stop the sidecar
```

## Use it from the toolkit
```bash
ra-ai "identify this hash and suggest a hashcat mode: $HASH"
ra-ai "what are the highest-value next steps here?" < engagements/<slug>/scans/<file>.nmap
```
Set `RA_AI_MODEL` in the toolkit to match the profile you started (defaults to `qwen2.5:3b`).

## About BaronLLM-v2
Qwen3-14B fine-tuned for offensive security, distributed as Q8_0 GGUF. It is a capable
**advisor**, not an oracle: it hallucinates commands and flags like any LLM, and its
public benchmark rankings are self-reported. Validate everything against real tool
behavior. We pull the weights at runtime (never re-host them); confirm the upstream
license terms before any redistribution. See `docs/TOOL-EVALUATIONS.md`.

## GPU acceleration
For fast inference, give the `ollama` service GPU access (nvidia-container-toolkit on the
host) — add the same `deploy.resources` nvidia block shown in `docker/docker-compose.yml`.
