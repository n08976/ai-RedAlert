# Skills

Curated offensive-security skills vendored from
[mukul975/Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills)
(Apache-2.0). Each skill is a `SKILL.md` (YAML frontmatter + workflow) that Claude Code and
other agentskills.io-compatible agents can load to run a task the way a senior analyst would.

## Scope of what we vendor
We keep only offensive-lab-relevant domains and skip the defensive/SOC/threat-intel bulk:

- `recon/` — network & service discovery, OSINT-lite, enumeration
- `web/` — web-application testing workflows
- `wifi/` — wireless assessment
- `cred-access/` — password/hash attacks, credential capture
- `exploitation/` — vulnerability validation & exploitation
- `post-exploitation/` — situational awareness, looting, pivoting

## Pulling / updating the subset
Skills are copied in deliberately (not a submodule) so the set stays small and auditable.
To refresh from upstream:

```bash
scripts/sync-skills.sh            # (added in a later commit) clones upstream, copies the
                                  # curated domains here, refreshes NOTICE.md
```

Until then, add a skill by dropping its folder here and noting the source in `NOTICE.md`.

## Using a skill
Inside the toolkit, point your agent at `skills/<domain>/<skill>/SKILL.md`, or read it
yourself as a runbook. Every skill assumes the same authorized-use rules as the rest of the
project — validate commands against your lab before trusting them.
