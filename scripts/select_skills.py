#!/usr/bin/env python3
"""
Select and vendor the offensive-relevant subset of Anthropic-Cybersecurity-Skills.

Classifies each upstream skill into a lab domain bucket by its frontmatter `tags` and
`subdomain` (not by fuzzy folder-name matching), copies the selected skills into
skills/<bucket>/, and regenerates skills/INDEX.md.

    python3 scripts/select_skills.py <path-to-upstream-clone>

Called by scripts/sync-skills.sh, which handles the shallow clone.
"""
from __future__ import annotations
import json, os, re, shutil, sys

BUCKET_TAGS = {
    "recon":            {"reconnaissance","recon","osint","enumeration","scanning","discovery","footprinting"},
    "web":              {"web","web-application","webapp","web-security","api","xss","sqli","ssrf","idor"},
    "wifi":             {"wifi","wireless","wpa","802.11","evil-twin","rogue-ap"},
    "cred-access":      {"credential-access","password","password-cracking","hash","brute-force","kerberoasting","responder","ntlm"},
    "exploitation":     {"exploitation","exploit","initial-access","payload","metasploit","rce","buffer-overflow"},
    "post-exploitation":{"post-exploitation","privilege-escalation","privesc","lateral-movement","persistence","pivoting","c2","active-directory","defense-evasion"},
}
OFF_SUBDOMAINS = {"red-teaming","penetration-testing","offensive-security","exploitation","red-team"}
BUCKET_ORDER = ["recon","web","wifi","cred-access","exploitation","post-exploitation"]


def frontmatter(path: str) -> dict:
    try:
        text = open(path, encoding="utf-8").read()
    except OSError:
        return {}
    m = re.search(r'^---\n(.*?)\n---', text, re.S)
    if not m:
        return {}
    fm, key = {}, None
    for line in m.group(1).splitlines():
        if re.match(r'^\w[\w-]*:', line):
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            fm[key] = val if val else []
        elif line.strip().startswith("- ") and isinstance(fm.get(key), list):
            fm[key].append(line.strip()[2:].strip())
    return fm


def bucket_for(fm: dict) -> str | None:
    tags = {t.lower() for t in (fm.get("tags") or [])}
    for b, keys in BUCKET_TAGS.items():
        if tags & keys:
            return b
    sub = (fm.get("subdomain") or "").lower()
    if sub in OFF_SUBDOMAINS or "red-team" in tags or "offensive-security" in tags:
        return "post-exploitation"
    return None


def main(up: str, dst_root: str = "skills") -> int:
    idx = json.load(open(f"{up}/index.json"))["skills"]
    selected: dict[str, list[str]] = {}
    for s in idx:
        p = os.path.join(up, "skills", s["name"], "SKILL.md")
        b = bucket_for(frontmatter(p))
        if b:
            selected.setdefault(b, []).append(s["name"])

    lines = ["# Curated offensive skills — index\n",
             "Vendored subset from "
             "[Anthropic-Cybersecurity-Skills](https://github.com/mukul975/Anthropic-Cybersecurity-Skills) "
             "(Apache-2.0). See NOTICE.md. Regenerate with scripts/sync-skills.sh.\n"]
    total = 0
    for bucket in BUCKET_ORDER:
        names = sorted(selected.get(bucket, []))
        if not names:
            continue
        bdir = os.path.join(dst_root, bucket)
        # clear old vendored content for this bucket, then repopulate
        if os.path.isdir(bdir):
            shutil.rmtree(bdir)
        os.makedirs(bdir, exist_ok=True)
        lines.append(f"\n## {bucket} ({len(names)})\n")
        for n in names:
            src = os.path.join(up, "skills", n)
            if not os.path.isdir(src):
                continue
            shutil.copytree(src, os.path.join(bdir, n))
            desc = ""
            m = re.search(r'^description:\s*(.+)$',
                          open(os.path.join(bdir, n, "SKILL.md"), encoding="utf-8").read(), re.M)
            if m:
                desc = m.group(1).strip()[:120]
            lines.append(f"- **{n}** — {desc}")
            total += 1
    open(os.path.join(dst_root, "INDEX.md"), "w").write("\n".join(lines) + "\n")
    print(f"[select_skills] vendored {total} offensive skills across {len(selected)} buckets")
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: select_skills.py <path-to-upstream-clone>", file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(sys.argv[1]))
