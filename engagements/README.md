# Engagements

Each subfolder here is one engagement's captured evidence, created by `ra new <name>`:

```
2026-09-20_lab-sweep/
├─ meta.yaml       engagement name, scope snapshot, start time
├─ commands.log    every ra-* invocation, timestamped
├─ scans/          raw tool output (auto-saved by wrappers)
├─ loot/           creds, hashes, pulled files
└─ notes.md        your running notes
```

**Everything here except this README is git-ignored** — captured results, loot, and creds
never get committed. This is your report-writing material; keep it local and wipe what you
no longer need.
