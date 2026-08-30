#!/usr/bin/env python3
"""
ai_attribution.py — AI-attribution-statement helper (Bryan Dollery's "agent 4").

Transparency, not concealment. Bryan's pipeline ends by appending a short
AI-assistance disclosure so the reader knows how the text was produced. This
helper does the deterministic part of that step:

  --check FILE   Report whether the post already carries a recognizable
                 AI-attribution statement (regex over common phrasings). Useful
                 as a WARN-ONLY pipeline gate ("transparency note present?").
  --emit         Print a ready-to-paste attribution statement (a few house
                 variants via --style). Does NOT modify any file — paste it
                 yourself so you stay in control of placement and wording.

Design notes
------------
- Detection-only / emit-only: this never edits a post. Appending a footer is a
  judgment call (placement, tone), so it stays with the author/LLM.
- WARN-ONLY: --check exits 0 by default even when the statement is missing. Use
  --strict to make a missing statement return exit 1 once the team enforces it.
- This is intentionally OPTIONAL in the pipeline. Some posts disclose AI use in
  the prose itself; this helper just makes the absence visible.

USAGE
-----
    python3 ai_attribution.py --check POST.md
    python3 ai_attribution.py --check --json POST.md
    python3 ai_attribution.py --emit                  # default 'footer' style
    python3 ai_attribution.py --emit --style inline
    python3 ai_attribution.py --emit --style frontmatter

EXIT CODES
----------
    0  statement present, OR --check warn-only (default), OR --emit
    1  --check --strict and no statement found
    2  usage / file error
"""
from __future__ import annotations

import argparse
import json
import re
import sys

# Recognizable AI-attribution phrasings (kept broad but anchored on "AI"+disclosure)
ATTRIBUTION_PATTERNS = [
    re.compile(r"\bAI[- ]assist(?:ed|ance)\b", re.I),
    re.compile(r"\bwritten with the (?:help|assistance) of (?:an? )?AI\b", re.I),
    re.compile(r"\b(?:drafted|written|created|produced|edited)\b[^.\n]{0,40}\bAI\b", re.I),
    re.compile(r"\bAI attribution\b", re.I),
    re.compile(r"\bgenerative AI\b[^.\n]{0,40}\b(?:assist|help|draft|write|edit)", re.I),
    re.compile(r"\b(?:large language model|LLM)\b[^.\n]{0,40}\b(?:assist|help|draft)", re.I),
    re.compile(r"\bhuman[- ](?:authored|reviewed|edited)\b[^.\n]{0,30}\bAI\b", re.I),
    re.compile(r"\bwith AI assistance\b", re.I),
]

# frontmatter key form, e.g.  ai_assistance: true  /  ai_attribution: "..."
FRONTMATTER_KEY_RE = re.compile(r"^\s*ai[_-](?:assistance|attribution|assisted)\s*:",
                                re.IGNORECASE | re.MULTILINE)

STATEMENTS = {
    "footer": (
        "---\n\n"
        "*AI attribution: this post was drafted with AI assistance and reviewed, "
        "edited, and fact-checked by the author. All claims are sourced; the "
        "opinions and final wording are mine.*"
    ),
    "inline": (
        "*Written with AI assistance, human-reviewed and fact-checked.*"
    ),
    "frontmatter": (
        "ai_assistance: true\n"
        "ai_attribution: \"Drafted with AI assistance; reviewed, edited, and "
        "fact-checked by the author.\""
    ),
}


def check_text(raw: str) -> dict:
    hits: list[str] = []
    for pat in ATTRIBUTION_PATTERNS:
        m = pat.search(raw)
        if m:
            hits.append(m.group(0).strip())
    fm = bool(FRONTMATTER_KEY_RE.search(raw))
    present = bool(hits) or fm
    return {
        "present": present,
        "prose_matches": hits,
        "frontmatter_key": fm,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="AI-attribution-statement helper.")
    ap.add_argument("paths", nargs="*", help="markdown file(s) for --check")
    ap.add_argument("--check", action="store_true", help="check whether a statement is present")
    ap.add_argument("--emit", action="store_true", help="print a ready-to-paste statement")
    ap.add_argument("--style", choices=sorted(STATEMENTS), default="footer",
                    help="statement style for --emit (default: footer)")
    ap.add_argument("--json", action="store_true", help="machine-readable --check output")
    ap.add_argument("--strict", action="store_true",
                    help="--check returns exit 1 when no statement is found")
    args = ap.parse_args()

    if args.emit:
        print(STATEMENTS[args.style])
        return 0

    if not args.check:
        ap.error("specify --check FILE... or --emit")

    if not args.paths:
        ap.error("--check requires at least one file")

    results = []
    any_missing = False
    for path in args.paths:
        try:
            with open(path, encoding="utf-8") as fh:
                raw = fh.read()
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        res = check_text(raw)
        res["path"] = path
        results.append(res)
        if not res["present"]:
            any_missing = True

    if args.json:
        print(json.dumps({"files": results,
                          "mode": "strict" if args.strict else "warn-only"},
                         indent=2, ensure_ascii=False))
    else:
        for res in results:
            print(f"\n=== {res['path']} ===")
            if res["present"]:
                where = []
                if res["prose_matches"]:
                    where.append(f"prose ({', '.join(res['prose_matches'][:3])})")
                if res["frontmatter_key"]:
                    where.append("frontmatter key")
                print(f"  ✅ AI attribution present — {'; '.join(where)}")
            else:
                print("  ⚠️  no AI-attribution statement found")
                print("     add one with:  python3 ai_attribution.py --emit")
        print("\n" + "=" * 56)
        if any_missing and not args.strict:
            print("RESULT: ⚠️  warn-only — attribution missing on ≥1 file; not blocked.")
        elif any_missing:
            print("RESULT: ❌ strict — attribution missing.")
        else:
            print("RESULT: ✅ attribution present on all files.")

    if args.strict and any_missing:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
