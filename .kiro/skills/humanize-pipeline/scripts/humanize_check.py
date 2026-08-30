#!/usr/bin/env python3
"""
humanize_check.py — deterministic gate wrapper for the humanize-pipeline skill.

Stage 1 (pre) and stage 3 (post) of the layered humanization pipeline:
runs the post-creation skill's ai_smell_scan.py on a post, converts its JSON
report into a fix-list (must_fix / should_fix / info), writes that JSON to
disk, and prints PASS/FAIL on the pipeline's exit criterion.

Exit criterion (stage 3): no must_fix findings, i.e. no ARTIFACT and no
hard-fail SIGNAL (em-dash-excessive / ai-vocabulary-strong /
ai-vocabulary-overused). Mirrors the scanner's own hard gate.

USAGE
    python3 humanize_check.py pre  POST.md [--out DIR]   # informational, exit 0
    python3 humanize_check.py post POST.md [--out DIR]   # gate, exit 1 on FAIL
    python3 humanize_check.py --self-test

The scanner location defaults to the repo-root scripts/ directory; override
with HUMANIZE_SCANNER=/path/to/ai_smell_scan.py.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HARD_FAIL_CATEGORIES = {
    "em-dash-excessive",
    "ai-vocabulary-strong",
    "ai-vocabulary-overused",
}

DEFAULT_SCANNER = (
    Path(__file__).resolve().parents[4] / "scripts" / "ai_smell_scan.py"
)


def scanner_path() -> Path:
    p = Path(os.environ.get("HUMANIZE_SCANNER", DEFAULT_SCANNER))
    if not p.is_file():
        sys.exit(f"error: scanner not found at {p} "
                 "(set HUMANIZE_SCANNER to override)")
    return p


def run_scan(post: Path) -> dict:
    """Run ai_smell_scan.py --json on `post` and return the parsed report."""
    proc = subprocess.run(
        [sys.executable, str(scanner_path()), "--json", str(post)],
        capture_output=True, text=True,
    )
    if proc.returncode == 2 or not proc.stdout.strip():
        sys.exit(f"error: scanner failed on {post}: {proc.stderr.strip()}")
    return json.loads(proc.stdout)


def build_fixlist(report: dict, phase: str) -> dict:
    """Classify scanner findings into the pipeline's fix-list tiers."""
    must_fix, should_fix, info = [], [], []
    stats = {}
    for f in report.get("files", []):
        stats = f.get("stats", {})
        for finding in f.get("findings", []):
            tier = finding.get("tier")
            cat = finding.get("category", "")
            entry = {
                "category": cat,
                "line": finding.get("line"),
                "snippet": finding.get("snippet"),
                "note": finding.get("note"),
            }
            if tier == "ARTIFACT" or cat in HARD_FAIL_CATEGORIES:
                must_fix.append(entry)
            elif tier == "SIGNAL":
                should_fix.append(entry)
            else:
                info.append(entry)
    return {
        "phase": phase,
        "path": report.get("files", [{}])[0].get("path"),
        "must_fix": must_fix,
        "should_fix": should_fix,
        "info": info,
        "stats": stats,
        "criterion_pass": not must_fix,
    }


def check(phase: str, post: Path, out_dir: Path) -> int:
    report = run_scan(post)
    fixlist = build_fixlist(report, phase)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{post.stem}.{phase}.json"
    out_file.write_text(json.dumps(fixlist, indent=2, ensure_ascii=False))

    verdict = "PASS" if fixlist["criterion_pass"] else "FAIL"
    print(f"[{phase}] {post.name}: {verdict} "
          f"(must_fix={len(fixlist['must_fix'])}, "
          f"should_fix={len(fixlist['should_fix'])}, "
          f"info={len(fixlist['info'])}) -> {out_file}")
    for e in fixlist["must_fix"]:
        print(f"    MUST-FIX L{e['line']}: [{e['category']}] {e['snippet']}")
    if phase == "post" and verdict == "FAIL":
        return 1
    return 0


def self_test() -> int:
    """Fixture check: seeded-bad text must FAIL post, clean text must PASS."""
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bad = tmp / "bad.md"
        bad.write_text(
            "---\ntitle: t\n---\n\n"
            "Let us delve into the rich tapestry of agent advertising.\n\n"
            "See https://example.com/?utm_source=chatgpt.com for more.\n"
        )
        good = tmp / "good.md"
        good.write_text(
            "---\ntitle: t\n---\n\n"
            "Agents pick tools by reading descriptions. That has a price tag "
            "attached now. I tried it on my own setup and the routing changed "
            "after a single paid listing.\n"
        )
        rc_bad = 0
        try:
            rc_bad = check("post", bad, tmp)
        except SystemExit:
            print("self-test: FAIL (scanner errored on fixture)")
            return 1
        rc_good = check("post", good, tmp)
        pre_rc = check("pre", bad, tmp)  # pre is informational: must exit 0

        bad_fix = json.loads((tmp / "bad.post.json").read_text())
        ok = (
            rc_bad == 1
            and rc_good == 0
            and pre_rc == 0
            and not bad_fix["criterion_pass"]
            and any(e["category"] == "ai-vocabulary-strong"
                    for e in bad_fix["must_fix"])
        )
        print(f"self-test: {'OK' if ok else 'FAIL'} "
              f"(bad post rc={rc_bad}, good post rc={rc_good}, pre rc={pre_rc})")
        return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("phase", nargs="?", choices=["pre", "post"],
                    help="pipeline phase (stage 1 = pre, stage 3 = post)")
    ap.add_argument("post", nargs="?", help="markdown file to check")
    ap.add_argument("--out", default=None,
                    help="directory for fix-list JSON (default: a fresh "
                         "private temp dir, printed in the result line)")
    ap.add_argument("--self-test", action="store_true",
                    help="run built-in fixture check")
    args = ap.parse_args()

    if args.self_test:
        return self_test()
    if not args.phase or not args.post:
        ap.error("phase and post file required (or use --self-test)")
    post = Path(args.post)
    if not post.is_file():
        sys.exit(f"error: no such file: {post}")
    out_dir = Path(args.out) if args.out else Path(tempfile.mkdtemp(prefix="humanize-"))
    return check(args.phase, post, out_dir)


if __name__ == "__main__":
    sys.exit(main())
