# Third-party attribution

This directory vendors a curated subset of skills from:

- **Anthropic-Cybersecurity-Skills** — https://github.com/mukul975/Anthropic-Cybersecurity-Skills
  - License: Apache-2.0
  - Copyright retained by the upstream authors/contributors.
  - Only offensive-lab-relevant skills are included; content may be lightly adapted for
    ai-RedAlert's paths and conventions. Upstream is the source of truth.

ai-RedAlert itself is Apache-2.0 (see repository root `LICENSE`). Vendored material remains
under its upstream license.

## This vendored subset
Selected by `scripts/select_skills.py` (classification by frontmatter tags/subdomain):
**208 offensive skills** across recon / web / wifi / cred-access / exploitation /
post-exploitation, out of 818 upstream. See `skills/INDEX.md` for the full list. Each
skill retains its upstream frontmatter, author, and Apache-2.0 license.
