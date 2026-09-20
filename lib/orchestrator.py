#!/usr/bin/env python3
"""
ai-RedAlert orchestrator — the "offensive mindset" engine.

Point it at a target (IP / hostname / URL / CIDR). It enumerates, parses the results into a
structured model, and reasons about the best next steps the way an operator would:

  1. Recon      — tiered nmap (discovery on a range, then service/version on live hosts).
  2. Model      — parse nmap XML into hosts -> open ports -> service/product/version.
  3. Triage     — per-service "plays" from a knowledge base, searchsploit hits on versions,
                  and matched offensive skills; optionally an LLM synthesises a ranked plan.
  4. Act        — run the SAFE enumeration / non-destructive vuln plays automatically and
                  capture output. Exploit plays are listed, not fired, unless --exploit.
  5. Report     — a ranked attack plan (markdown) in the engagement + a stdout summary.

Everything is scope-gated (lib/scope.py) and captured (lib/evidence.py).
"""
from __future__ import annotations

import ipaddress
import os
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from urllib.parse import urlparse

import scope as scope_mod
import evidence

# ── data model ────────────────────────────────────────────────────────────────
@dataclass
class Service:
    port: int
    proto: str
    name: str
    product: str = ""
    version: str = ""
    tunnel: str = ""          # "ssl" when the service is TLS-wrapped
    extrainfo: str = ""

    @property
    def banner(self) -> str:
        return " ".join(x for x in (self.product, self.version, self.extrainfo) if x).strip()


@dataclass
class Host:
    ip: str
    hostname: str = ""
    services: list[Service] = field(default_factory=list)


@dataclass
class Play:
    """A recommended next step for a service."""
    title: str
    cmd: str                  # exact command, {host}/{port} already substituted
    phase: str                # "enum" | "vuln" | "exploit"
    technique: str = ""       # MITRE ATT&CK id
    skill: str = ""           # relevant vendored skill name
    note: str = ""


# ── service knowledge base ────────────────────────────────────────────────────
# Maps an nmap service name (or a well-known port) to ordered plays. Templates use
# {host} and {port}. Keep enum/vuln plays non-destructive; mark real exploitation "exploit".
def _kb() -> dict:
    return {
        "ftp": [
            Play("Anonymous FTP login check", "nmap -p{port} --script ftp-anon {host}", "enum", "T1078.001", "testing-ftp-services-for-vulnerabilities"),
            Play("FTP version / vuln scripts", "nmap -p{port} --script ftp-* -sV {host}", "vuln", "T1190"),
        ],
        "ssh": [
            Play("SSH auth methods & host key", "nmap -p{port} --script ssh-auth-methods,ssh2-enum-algos {host}", "enum", "T1021.004"),
            Play("SSH user/password spray (dictionary)", "ra-hydra -L users.txt -P /usr/share/wordlists/rockyou.txt ssh://{host}:{port}", "exploit", "T1110.001", "conducting-password-spraying-attacks",
                 note="Online guessing — noisy and can lock accounts. Use a small, targeted list."),
        ],
        "telnet": [Play("Telnet banner / default creds", "nmap -p{port} --script telnet-encryption,telnet-ntlm-info {host}", "enum", "T1078")],
        "smtp": [Play("SMTP user enumeration", "nmap -p{port} --script smtp-enum-users,smtp-commands {host}", "enum", "T1087")],
        "domain": [Play("DNS zone transfer attempt", "dig axfr @{host} <domain>", "enum", "T1590.002")],
        "http": _web_plays(),
        "https": _web_plays(tls=True),
        "http-proxy": _web_plays(),
        "http-alt": _web_plays(),
        "ssl/http": _web_plays(tls=True),
        "microsoft-ds": _smb_plays(),
        "netbios-ssn": _smb_plays(),
        "snmp": [
            Play("SNMP community strings (onesixtyone)", "onesixtyone -c /usr/share/seclists/Discovery/SNMP/common-snmp-community-strings.txt {host}", "enum", "T1046"),
            Play("SNMP walk (if 'public')", "snmpwalk -v2c -c public {host}", "enum", "T1602.001"),
        ],
        "ldap": [Play("LDAP anonymous bind / naming contexts", "nmap -p{port} --script ldap-rootdse,ldap-search {host}", "enum", "T1087.002")],
        "ms-sql-s": [
            Play("MSSQL info & default creds", "nmap -p{port} --script ms-sql-info,ms-sql-empty-password {host}", "enum", "T1078"),
            Play("MSSQL brute (dictionary)", "ra-hydra -L users.txt -P pass.txt mssql://{host}", "exploit", "T1110.001"),
        ],
        "mysql": [Play("MySQL info & empty-password check", "nmap -p{port} --script mysql-info,mysql-empty-password {host}", "enum", "T1078")],
        "ms-wbt-server": [
            Play("RDP security / NLA check", "nmap -p{port} --script rdp-enum-encryption,rdp-ntlm-info {host}", "enum", "T1021.001"),
            Play("RDP dictionary attack", "ra-hydra -L users.txt -P pass.txt rdp://{host}", "exploit", "T1110.001", note="Locks accounts fast — targeted lists only."),
        ],
        "vnc": [Play("VNC auth / no-auth check", "nmap -p{port} --script vnc-info,realvnc-auth-bypass {host}", "vuln", "T1021.005")],
        "redis": [Play("Redis unauthenticated access", "redis-cli -h {host} -p {port} info", "enum", "T1078")],
        "mongodb": [Play("MongoDB unauthenticated access", "nmap -p{port} --script mongodb-info {host}", "enum", "T1078")],
        "rpcbind": [Play("RPC / NFS exports", "showmount -e {host}", "enum", "T1135")],
        "nfs": [Play("NFS exports & mounts", "showmount -e {host}", "enum", "T1135")],
    }


def _web_plays(tls: bool = False) -> list:
    scheme = "https" if tls else "http"
    return [
        Play("HTTP fingerprint & headers", "nmap -p{port} --script http-title,http-headers,http-methods,http-server-header {host}", "enum", "T1595.002"),
        Play("Directory / content discovery", f"gobuster dir -u {scheme}://{{host}}:{{port}} -w /usr/share/seclists/Discovery/Web-Content/common.txt", "enum", "T1595.003", "performing-web-content-discovery"),
        Play("Web vuln scan (nikto)", f"nikto -h {scheme}://{{host}}:{{port}}", "vuln", "T1190", "scanning-web-applications-for-vulnerabilities"),
        Play("Known-vuln HTTP scripts", "nmap -p{port} --script http-enum,http-vuln* -sV {host}", "vuln", "T1190"),
    ]


def _smb_plays() -> list:
    return [
        Play("SMB shares & sessions (netexec)", "nxc smb {host} -u '' -p '' --shares", "enum", "T1135", "enumerating-smb-shares-and-sessions"),
        Play("SMB OS / signing / null session", "enum4linux-ng -A {host}", "enum", "T1087", "enumerating-windows-domain-with-enum4linux"),
        Play("SMB known-vuln scripts (MS17-010 etc.)", "nmap -p{port} --script smb-vuln* {host}", "vuln", "T1210", "identifying-smb-vulnerabilities"),
        Play("SMB password spray", "nxc smb {host} -u users.txt -p pass.txt --continue-on-success", "exploit", "T1110.003"),
    ]


PORT_HINTS = {21: "ftp", 22: "ssh", 23: "telnet", 25: "smtp", 53: "domain", 80: "http",
              110: "pop3", 111: "rpcbind", 135: "msrpc", 139: "netbios-ssn", 143: "imap",
              161: "snmp", 389: "ldap", 443: "https", 445: "microsoft-ds", 1433: "ms-sql-s",
              1521: "oracle", 2049: "nfs", 3306: "mysql", 3389: "ms-wbt-server", 5432: "postgresql",
              5900: "vnc", 6379: "redis", 8080: "http-proxy", 8443: "https", 27017: "mongodb"}
PHASE_RANK = {"enum": 0, "vuln": 1, "exploit": 2}


# ── target handling ───────────────────────────────────────────────────────────
def classify_target(target: str) -> tuple[str, str]:
    """Return (kind, host) where kind in {url, cidr, host}."""
    if re.match(r'^https?://', target, re.I):
        return "url", urlparse(target).hostname or target
    try:
        net = ipaddress.ip_network(target, strict=False)
        return ("cidr" if net.num_addresses > 1 else "host"), target
    except ValueError:
        return "host", target


# ── recon ─────────────────────────────────────────────────────────────────────
def _run(cmd: list[str], timeout: int = 1800) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def discover_hosts(cidr: str) -> list[str]:
    excl = scope_mod.excluded_hosts_in(cidr)
    cmd = ["nmap", "-sn", "-n", cidr]
    if excl:
        cmd += ["--exclude", ",".join(excl)]
    cp = _run(cmd)
    return re.findall(r'Nmap scan report for ([\d.]+)', cp.stdout)


def scan_host(host: str, full: bool = False) -> Host:
    """Service/version scan of one host; returns a parsed Host."""
    xml_out = str(evidence.scan_path(f"nmap_{host.replace('/', '-')}.xml"))
    ports = "-p-" if full else "--top-ports=1000"
    cmd = ["nmap", "-sV", "-sC", "-n", "-Pn", ports, "--open", "-oX", xml_out, host]
    excl = scope_mod.excluded_hosts_in(host)
    if excl:
        cmd += ["--exclude", ",".join(excl)]
    evidence.log_command(["ra-auto:scan"] + cmd)
    _run(cmd)
    return parse_nmap_xml(xml_out, host)


def parse_nmap_xml(path: str, fallback_ip: str = "") -> Host:
    host = Host(ip=fallback_ip)
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, FileNotFoundError):
        return host
    h = root.find("host")
    if h is None:
        return host
    addr = h.find("address[@addrtype='ipv4']")
    if addr is not None:
        host.ip = addr.get("addr", fallback_ip)
    hn = h.find("hostnames/hostname")
    if hn is not None:
        host.hostname = hn.get("name", "")
    for p in h.findall("ports/port"):
        st = p.find("state")
        if st is None or st.get("state") != "open":
            continue
        svc = p.find("service")
        s = Service(port=int(p.get("portid")), proto=p.get("protocol", "tcp"),
                    name=(svc.get("name", "") if svc is not None else ""))
        if svc is not None:
            s.product = svc.get("product", "")
            s.version = svc.get("version", "")
            s.tunnel = svc.get("tunnel", "")
            s.extrainfo = svc.get("extrainfo", "")
        host.services.append(s)
    return host


# ── triage ────────────────────────────────────────────────────────────────────
def searchsploit(query: str) -> list[str]:
    if not query or not shutil.which("searchsploit"):
        return []
    try:
        cp = _run(["searchsploit", "--color=never", query], timeout=60)
    except subprocess.SubprocessError:
        return []
    hits = [ln.strip() for ln in cp.stdout.splitlines()
            if ln.strip() and "----" not in ln and "Exploit Title" not in ln
            and "No Results" not in ln and "Shellcodes" not in ln]
    return hits[:5]


def plays_for(svc: Service) -> list[Play]:
    kb = _kb()
    key = svc.name.lower()
    if key not in kb:
        key = PORT_HINTS.get(svc.port, "")
    if svc.tunnel == "ssl" and key == "http":
        key = "https"
    plays = kb.get(key, [])
    out = []
    for p in plays:
        out.append(Play(p.title, p.cmd.format(host="{host}", port=svc.port).replace("{host}", "%HOST%"),
                        p.phase, p.technique, p.skill, p.note))
    return out


def triage_host(host: Host) -> list[dict]:
    """Build ranked findings for a host: each is {service, plays, exploits}."""
    findings = []
    for svc in sorted(host.services, key=lambda s: s.port):
        plays = [Play(p.title, p.cmd.replace("%HOST%", host.ip), p.phase, p.technique, p.skill, p.note)
                 for p in plays_for(svc)]
        exploits = searchsploit(f"{svc.product} {svc.version}".strip()) if svc.product else []
        findings.append({"service": svc, "plays": plays, "exploits": exploits})
    return findings


# ── skill matching ────────────────────────────────────────────────────────────
def match_skills(host: Host, limit: int = 6) -> list[str]:
    """Vendored offensive skills relevant to what we found (by service keywords)."""
    root = os.path.join(os.environ.get("REDALERT_HOME", "/opt/redalert"), "skills")
    if not os.path.isdir(root):
        return []
    names = []
    for bucket in os.listdir(root):
        bpath = os.path.join(root, bucket)
        if os.path.isdir(bpath):
            names += [(bucket, n) for n in os.listdir(bpath) if os.path.isdir(os.path.join(bpath, n))]
    keywords = set()
    for s in host.services:
        for tok in re.split(r'[-_/ ]', f"{s.name} {s.product}".lower()):
            if len(tok) > 2:
                keywords.add(tok)
    keywords |= {"reconnaissance", "enumeration"} if host.services else set()
    scored = []
    for bucket, n in names:
        hits = sum(1 for k in keywords if k in n.lower())
        if hits:
            scored.append((hits, f"{bucket}/{n}"))
    scored.sort(reverse=True)
    return [n for _, n in scored[:limit]]


# ── LLM synthesis (optional) ──────────────────────────────────────────────────
def llm_available() -> bool:
    host = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    try:
        import urllib.request
        urllib.request.urlopen(f"{host}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def llm_synthesize(host: Host, findings: list[dict], skills: list[str]) -> str:
    """Ask the local LLM to rank findings into a concrete attack plan. Empty on failure."""
    api = os.environ.get("OLLAMA_HOST", "http://ollama:11434")
    model = os.environ.get("RA_AI_MODEL", "qwen2.5:3b")
    lines = [f"Target host {host.ip}" + (f" ({host.hostname})" if host.hostname else "") + " — open services:"]
    for f in findings:
        s = f["service"]
        lines.append(f"  - {s.port}/{s.proto} {s.name} {s.banner}".rstrip())
        for ex in f["exploits"][:3]:
            lines.append(f"      possible exploit: {ex}")
    if skills:
        lines.append("Relevant playbooks available: " + ", ".join(skills))
    facts = "\n".join(lines)
    system = ("You are an offensive-security operator assisting an AUTHORIZED penetration test "
              "in the operator's own lab. Given enumeration results, produce a PRIORITISED, "
              "concrete attack plan: which services to attack first and why, the exact tools/"
              "commands to run, and the most promising exploitation path. Be specific and "
              "technical. Number the steps by priority. Do not include disclaimers.")
    prompt = f"{facts}\n\nGive the prioritised next-step attack plan."
    try:
        import json as _json, urllib.request
        req = urllib.request.Request(
            f"{api}/api/generate",
            data=_json.dumps({"model": model, "system": system, "prompt": prompt, "stream": False}).encode(),
            headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return _json.loads(r.read()).get("response", "").strip()
    except Exception as e:
        return f"(LLM synthesis unavailable: {e})"


# ── reporting ─────────────────────────────────────────────────────────────────
def build_report(host: Host, findings: list[dict], skills: list[str], llm_text: str) -> str:
    md = [f"# Attack plan — {host.ip}" + (f" ({host.hostname})" if host.hostname else ""), ""]
    if not findings:
        md.append("_No open services found (host may be down/filtered, or all ports closed)._")
        return "\n".join(md)
    md.append("## Open services & recommended plays\n")
    for f in findings:
        s = f["service"]
        md.append(f"### {s.port}/{s.proto} — {s.name} {s.banner}".rstrip())
        for p in f["plays"]:
            tag = {"enum": "🔍", "vuln": "🧪", "exploit": "💥"}.get(p.phase, "•")
            md.append(f"- {tag} **{p.title}** `{p.technique}`")
            md.append(f"  ```\n  {p.cmd}\n  ```")
            if p.note:
                md.append(f"  > {p.note}")
            if p.skill:
                md.append(f"  · skill: `{p.skill}`")
        for ex in f["exploits"]:
            md.append(f"- 💥 searchsploit: `{ex}`")
        md.append("")
    if skills:
        md.append("## Relevant vendored playbooks\n" + "\n".join(f"- `{s}`" for s in skills) + "\n")
    if llm_text:
        md.append("## Operator plan (LLM-synthesised)\n\n" + llm_text + "\n")
    md.append("_🔍 safe enum · 🧪 non-destructive vuln check · 💥 exploitation (run deliberately)._")
    return "\n".join(md)


# ── act: run the safe plays automatically ─────────────────────────────────────
def _runnable(play: Play) -> bool:
    if play.phase == "exploit":
        return False
    if "<" in play.cmd:
        return False
    if re.search(r'\b(users?\.txt|pass\.txt|password\.txt)\b', play.cmd):
        return False
    tool = play.cmd.split()[0]
    return bool(shutil.which(tool) or tool.startswith("ra-"))


def execute_safe(findings: list[dict], run_exploit: bool = False) -> list[tuple[str, str]]:
    import shlex
    results = []
    for f in findings:
        for p in f["plays"]:
            if p.phase == "exploit" and not run_exploit:
                continue
            if not _runnable(p) and not (run_exploit and p.phase == "exploit"):
                continue
            slug = re.sub(r'[^A-Za-z0-9]+', '_', p.title).strip('_')[:28]
            out_path = str(evidence.scan_path(f"play_{slug}.txt"))
            evidence.log_command(["ra-auto:play", p.cmd])
            try:
                cp = _run(shlex.split(p.cmd), timeout=600)
                with open(out_path, "w") as fh:
                    fh.write(f"$ {p.cmd}\n\n{cp.stdout}\n{cp.stderr}")
                results.append((p.title, out_path))
            except Exception as e:
                results.append((p.title, f"(failed: {e})"))
    return results


# ── main flow ─────────────────────────────────────────────────────────────────
def orchestrate(target: str, full: bool = False, run_exploit: bool = False,
                use_llm: bool = True, do_act: bool = True) -> str:
    kind, host_str = classify_target(target)
    scope_mod.check_target(host_str)

    targets = discover_hosts(target) if kind == "cidr" else [host_str]
    if kind == "cidr":
        print(f"[auto] {len(targets)} live host(s) in {target}: {', '.join(targets) or '(none)'}")

    reports = []
    for ip in targets:
        print(f"[auto] enumerating {ip} …")
        host = scan_host(ip, full=full)
        findings = triage_host(host)
        skills = match_skills(host)
        n_open = len(host.services)
        print(f"[auto] {ip}: {n_open} open port(s)"
              + (": " + ", ".join(f"{s.port}/{s.name}" for s in host.services) if n_open else ""))

        acted = []
        if do_act and findings:
            print(f"[auto] running safe enumeration plays"
                  + (" + exploitation" if run_exploit else "") + " …")
            acted = execute_safe(findings, run_exploit=run_exploit)
            for title, path in acted:
                print(f"       ✓ {title} -> {path}")

        llm_text = ""
        if use_llm and findings and llm_available():
            print("[auto] synthesising attack plan with local LLM …")
            llm_text = llm_synthesize(host, findings, skills)

        report_md = build_report(host, findings, skills, llm_text)
        rpath = evidence.scan_path(f"attackplan_{ip.replace('/', '-')}.md")
        with open(rpath, "w") as fh:
            fh.write(report_md)
        reports.append(str(rpath))
        print(f"[auto] attack plan -> {rpath}\n")

    return "\n".join(reports)


# ── explicit mode: run only chosen categories ─────────────────────────────────
CATEGORY_SERVICES = {
    "web": {"http", "https", "http-proxy", "http-alt", "ssl/http"},
    "smb": {"microsoft-ds", "netbios-ssn"},
    "ssh": {"ssh"}, "ftp": {"ftp"}, "snmp": {"snmp"}, "ldap": {"ldap"},
    "db": {"mysql", "ms-sql-s", "postgresql", "mongodb", "redis", "oracle"},
    "rdp": {"ms-wbt-server"}, "vnc": {"vnc"},
}


def run_categories(target: str, categories: list[str], run_exploit: bool = False) -> str:
    kind, host_str = classify_target(target)
    scope_mod.check_target(host_str)
    wanted = set()
    for c in categories:
        wanted |= CATEGORY_SERVICES.get(c, set())
    ips = discover_hosts(target) if kind == "cidr" else [host_str]
    out = []
    for ip in ips:
        print(f"[run] enumerating {ip} (categories: {', '.join(categories)}) …")
        host = scan_host(ip)
        host.services = [s for s in host.services if s.name.lower() in wanted or PORT_HINTS.get(s.port) in wanted]
        if not host.services:
            print(f"[run] {ip}: none of the requested services are open"); continue
        findings = triage_host(host)
        acted = execute_safe(findings, run_exploit=run_exploit)
        for title, path in acted:
            print(f"       ✓ {title} -> {path}")
        rpath = evidence.scan_path(f"run_{ip.replace('/', '-')}.md")
        with open(rpath, "w") as fh:
            fh.write(build_report(host, findings, match_skills(host), ""))
        out.append(str(rpath)); print(f"[run] report -> {rpath}")
    return "\n".join(out)


# ── CLI ───────────────────────────────────────────────────────────────────────
def cli(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="ra auto/run", add_help=True,
                                 description="Offensive-mindset orchestrator (authorized targets only).")
    ap.add_argument("target", help="IP / hostname / URL / CIDR range")
    ap.add_argument("--full", action="store_true", help="scan all 65535 ports (slower)")
    ap.add_argument("--exploit", action="store_true", help="also run exploitation plays (deliberate)")
    ap.add_argument("--no-act", action="store_true", help="plan only; do not run any plays")
    ap.add_argument("--no-llm", action="store_true", help="skip LLM synthesis")
    ap.add_argument("--only", default="", help="explicit mode: comma-separated categories "
                    "(web,smb,ssh,ftp,snmp,ldap,db,rdp,vnc)")
    args = ap.parse_args(argv)
    try:
        if args.only:
            cats = [c.strip() for c in args.only.split(",") if c.strip()]
            print(run_categories(args.target, cats, run_exploit=args.exploit))
        else:
            orchestrate(args.target, full=args.full, run_exploit=args.exploit,
                        use_llm=not args.no_llm, do_act=not args.no_act)
    except scope_mod.ScopeError as e:
        print(f"✗ out of scope: {e}", file=__import__("sys").stderr); return 3
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(cli(sys.argv[1:]))
