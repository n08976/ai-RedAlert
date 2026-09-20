# Rules of Engagement

ai-RedAlert is an offensive-security toolkit. Offensive tools are neutral; the legality
and ethics live entirely in **where you point them**. These rules are non-negotiable for
this project.

## 1. Authorization is a precondition, not a formality
Only test systems you **own** or have **explicit written permission** to assess. For a
home lab that means machines and networks you built. For an engagement that means a signed
scope/authorization document. No authorization → no testing. Full stop.

## 2. Scope is enforced in code, not just on paper
Every `ra-*` wrapper checks its target against `scope/scope.yaml` and **fails closed** —
no scope file, an expired scope, or an unlisted target means the tool refuses to run.
This is a safety net, not a substitute for judgment. Do not edit the scope file to include
something you are not authorized to touch.

## 3. Keep the lab isolated
Run your vulnerable targets (Metasploitable, VulnHub/HTB-style VMs, your own build) on an
**isolated network segment** with no route to systems you don't own and no bridge to
production or the public internet beyond what the exercise needs. Wi-Fi testing in
particular must use **your own** APs/clients — capturing or deauthing networks you don't
own is illegal in most jurisdictions.

## 4. Handle captured data responsibly
Hashes, credentials, and loot land in `engagements/<name>/loot/`, which is git-ignored.
Keep it there. Don't commit it, don't reuse real-world credentials, wipe engagements you
no longer need.

## 5. Certification context
This lab is built for OSCP / PNPT / CPTS / eJPT-style preparation. Those exams provide
their own authorized environments with their own rules — follow the exam's rules of
engagement when practicing against exam infrastructure. This toolkit is for **your** lab
and authorized practice targets.

## 6. If you find a real vulnerability in someone else's system
Stop. You are out of scope. Follow coordinated disclosure; do not exploit further.

---
By using ai-RedAlert you accept sole responsibility for staying inside these rules and the
law. The maintainers provide the toolkit for authorized testing and assume no liability
for misuse.
