#!/usr/bin/env python3
"""
leak_scan.py — deterministic internal-knowledge-leak scanner for publishable content.

Backs the "Claim Verification & Internal-Leak Audit" pipeline gate (post-creation
Step 11d). Scans a Markdown/text file for markers that must NEVER appear in a public
artifact.

Two pattern sources:
  1. BUILT-IN generic patterns (always applied, org-neutral): personal filesystem
     paths, home paths, and 12-digit cloud account IDs.
  2. ORG-SPECIFIC patterns loaded from a JSON config, so this public tool ships
     org-neutral and each user adds THEIR OWN organization's internal markers
     (internal email domains, chat/wiki/tool links, internal hostnames, codenames).

Org-pattern config resolution (first match wins):
      --patterns FILE  >  $LEAK_PATTERNS_CONFIG  >  config/leak-patterns.local.json
      >  config/leak-patterns.sample.json

Copy config/leak-patterns.sample.json to config/leak-patterns.local.json (gitignored)
and put YOUR organization's markers there — they stay local and never ship publicly.

Usage:
  python3 leak_scan.py <file.md> [--aliases a,b,...] [--patterns FILE] [--json]
Exit code: 0 = clean, 1 = leak(s) found (hard gate).
"""
import argparse
import json
import os
import re
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
_CFG_DIR = _REPO_ROOT / "config"

# Built-in, ORG-NEUTRAL patterns — always applied. (label, regex, note)
BUILTIN_PATTERNS = [
    ("cloud-account-id", r'(?<!\d)\d{12}(?!\d)',      "12-digit cloud account ID"),
    ("personal-path",    r'/Users/[A-Za-z0-9._-]+/',  "personal filesystem path"),
    ("home-path",        r'/home/[A-Za-z0-9._-]+/',   "personal home path"),
]
# 12-digit placeholders explicitly safe to publish.
ACCOUNT_ID_ALLOW = {"123456789012"}


def _resolve_patterns_file(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    env = os.environ.get("LEAK_PATTERNS_CONFIG")
    if env:
        return Path(env)
    local = _CFG_DIR / "leak-patterns.local.json"
    if local.exists():
        return local
    return _CFG_DIR / "leak-patterns.sample.json"


def load_org_patterns(explicit: str | None = None):
    """Load org-specific (label, regex, note) tuples from the resolved config file."""
    p = _resolve_patterns_file(explicit)
    try:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []
    out = []
    for e in data.get("patterns", []):
        rx = e.get("regex")
        if not rx:
            continue
        try:
            re.compile(rx)
        except re.error:
            sys.stderr.write(f"leak_scan: skipping invalid regex for '{e.get('label')}'\n")
            continue
        out.append((e.get("label", "org-internal"), rx, e.get("note", "organization-internal marker")))
    return out


def scan(text, aliases, org_patterns):
    findings = []
    for label, rx, note in BUILTIN_PATTERNS + list(org_patterns):
        for m in re.finditer(rx, text, re.IGNORECASE):
            val = m.group(0)
            if label == "cloud-account-id" and val in ACCOUNT_ID_ALLOW:
                continue
            line = text.count("\n", 0, m.start()) + 1
            findings.append({"label": label, "match": val, "line": line, "note": note})
    for alias in aliases:
        alias = alias.strip()
        if not alias:
            continue
        for m in re.finditer(r'\b' + re.escape(alias) + r'\b', text):
            line = text.count("\n", 0, m.start()) + 1
            findings.append({"label": "internal-alias", "match": alias, "line": line,
                             "note": "internal alias"})
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--aliases", default="", help="comma-separated internal aliases to flag")
    ap.add_argument("--patterns", default="", help="org-pattern JSON file (overrides config resolution)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    text = open(a.file, encoding="utf-8").read()
    org_patterns = load_org_patterns(a.patterns or None)
    findings = scan(text, a.aliases.split(",") if a.aliases else [], org_patterns)
    if a.json:
        print(json.dumps({"file": a.file, "leaks": findings, "clean": not findings}, indent=2))
    else:
        if not findings:
            print(f"✅ leak_scan: clean — no internal markers in {a.file}")
        else:
            print(f"❌ leak_scan: {len(findings)} internal marker(s) in {a.file} — BLOCK publish:")
            for f in findings:
                print(f"  L{f['line']}: [{f['label']}] '{f['match']}' — {f['note']}")
    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()
