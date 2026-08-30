#!/usr/bin/env python3
"""
verify_citations.py — content-pipeline VERIFICATION gate (P0).

The deterministic harness for the verification half of the content pipeline —
the gap the AI-smell check does NOT cover (smell = *style*; this = *substance*).
See 06-knowledge/tools/ai-smell-check-improvements.md (P0.1) and the (until now
unenforced) mandate in steering/core/ground-truth.md:

    "Do NOT present product/feature claims to the user until you have fetched at
     least one official doc source in the same turn."

This script implements Bryan Dollery's "agent 1" (existence + support) as far as
a deterministic script honestly can, and hands the genuinely-semantic part off
to an explicit LLM-judgment sub-step (the worklist below). It does THREE things:

  (1) REFERENCE EXISTENCE  (deterministic)
      - every inline `[N]` citation marker has a matching `[N] ...` entry in the
        Sources / References section  (else: UNDEFINED citation);
      - every Sources entry carries a URL and that URL RESOLVES (curl, bounded,
        headless-safe — auth/rate-limit => UNVERIFIED, not BROKEN);
      - Sources entries that are never cited inline are flagged ORPHAN
        (Wikipedia "named refs declared but unused" tell).

  (2) CLAIM -> SOURCE SUPPORT  (deterministic harness + LLM judgment)
      For every inline citation, extract the sentence that carries it (the
      "claim"), pair it with its source {title,url}, optionally fetch a text
      excerpt of the source (--fetch), and emit a SUPPORT WORKLIST. Whether the
      source actually supports the claim "on the whole" is a semantic judgment a
      regex cannot make, so each item is marked `support: "NEEDS_LLM_JUDGMENT"`.
      Two ways to resolve it:
        * default  — emit the worklist (JSON with --json) for the pipeline's
                     LLM Step 11c to judge;
        * --judge-cmd CMD — pipe each item as JSON to an external LLM command
                     that prints one of SUPPORTED / PARTIAL / NOT_SUPPORTED /
                     UNCLEAR on stdout (best-effort; confidence flagged).

  (3) UNCITED FACTUAL CLAIMS  (heuristic, advisory)
      Sentences that assert product behavior, availability, version numbers,
      quotas, pricing, or percentages but carry NO citation — exactly what
      ground-truth.md says must be sourced. Heuristic => REVIEW tier, never a
      hard gate (keeps false positives out of the build).

WARN-ONLY BY DESIGN
-------------------
This is wired into the pipeline as a WARN-ONLY gate. The default exit code is 0
even when issues are found, so it never hard-fails a build. Use --strict to make
EXISTENCE failures (undefined citations, confirmed-broken source URLs) return a
non-zero exit once the team is ready to enforce. SUPPORT judgments and uncited-
claim heuristics NEVER affect the exit code.

USAGE
-----
    python3 verify_citations.py POST.md [MORE.md ...]
    python3 verify_citations.py --json POST.md            # machine-readable
    python3 verify_citations.py --fetch POST.md           # fetch source excerpts
    python3 verify_citations.py --no-external POST.md      # skip URL resolution
    python3 verify_citations.py --strict POST.md           # existence => exit 1
    python3 verify_citations.py --judge-cmd "my-llm" POST.md   # auto-judge support

EXIT CODES
----------
    0  warn-only (default), or strict with no existence failures
    1  --strict and at least one UNDEFINED citation or BROKEN source URL
    2  usage / file error

Detection-only: never rewrites the post.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass, field, asdict

# --------------------------------------------------------------------------- #
# code / structure stripping (offsets & line numbers preserved by blanking)
# --------------------------------------------------------------------------- #

FENCE_RE = re.compile(r"(^|\n)(```|~~~).*?(\n)(?:.*?\n)??\2[ \t]*(?=\n|$)", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---[ \t]*(?=\n|$)", re.DOTALL)
SOURCES_HEADING_RE = re.compile(r"^#{1,6}\s+(sources|references|footnotes)\b.*$",
                                re.IGNORECASE | re.MULTILINE)

URL_RE = re.compile(r"https?://[^\s)\]>\"']+")
# markdown link target: ](URL) where URL is absolute or a relative /path
MD_TARGET_RE = re.compile(r"\]\(\s*(?P<url>/[^)\s]+|https?://[^)\s]+)")
# bare relative site path, e.g. /blog/foo/  (not a date like /2026)
REL_URL_RE = re.compile(r"(?<![\w)])(/[a-zA-Z][^\s)\]>\"']*)")
# inline citation marker: [N] or [N, M] — NOT a markdown link [text](url) or
# reference-style link [text][ref]. A trailing ':' is allowed: in the body
# (the Sources block is stripped before this runs) "...above [2]:" is a real
# citation that merely precedes a colon, not a [label]: link definition.
INLINE_CITE_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\](?!\(|\[)")
# Sources entry line: starts with [N] (optionally a list bullet, optionally [N]:)
SOURCE_ENTRY_RE = re.compile(r"^\s{0,3}(?:[-*+]\s+)?\[(\d+)\]:?\s+(.*\S)\s*$", re.MULTILINE)


def _blank(m: re.Match) -> str:
    return re.sub(r"[^\n]", " ", m.group(0))


def strip_code(text: str) -> str:
    text = FENCE_RE.sub(_blank, text)
    text = INLINE_CODE_RE.sub(_blank, text)
    return text


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub(_blank, text)


def split_body_sources(text: str) -> tuple[str, str, int]:
    """Return (body, sources_block, sources_start_offset).
    body = everything before the Sources heading (prose where claims live);
    sources_block = the Sources heading to EOF."""
    m = SOURCES_HEADING_RE.search(text)
    if not m:
        return text, "", -1
    return text[: m.start()], text[m.start():], m.start()


def line_of(offset: int, text: str) -> int:
    return text.count("\n", 0, offset) + 1


def sentence_around(text: str, offset: int) -> str:
    """Extract the sentence containing `offset` (rough sentence segmentation)."""
    start = 0
    for m in re.finditer(r"(?<=[.!?])\s+|\n\s*\n", text[:offset]):
        start = m.end()
    end_m = re.search(r"[.!?](?:\s|$)|\n\s*\n", text[offset:])
    end = offset + end_m.end() if end_m else len(text)
    return re.sub(r"\s+", " ", text[start:end]).strip()


# --------------------------------------------------------------------------- #
# URL resolution (shared shape with scripts/check-links.py)
# --------------------------------------------------------------------------- #

def check_url(url: str, timeout: int = 10) -> tuple[str, str]:
    """Return (status, detail). status in {OK, BROKEN, UNVERIFIED}."""
    try:
        out = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-L",
             "--max-time", str(timeout), url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        code = out.stdout.strip()
        if code in ("", "000"):
            return "UNVERIFIED", "no response (offline/timeout)"
        if code[0] in "23":
            return "OK", code
        if code in ("401", "403", "405", "429", "503"):
            return "UNVERIFIED", f"HTTP {code} (not fetchable, likely valid)"
        return "BROKEN", f"HTTP {code}"
    except Exception as exc:  # noqa: BLE001
        return "UNVERIFIED", f"check error: {exc}"


def fetch_excerpt(url: str, max_chars: int = 1500, timeout: int = 12) -> str:
    """Best-effort plain-text excerpt of a URL for the LLM support judgment.
    Strips tags crudely; stdlib-only. Returns "" on any failure."""
    try:
        out = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout),
             "-A", "Mozilla/5.0 (verify_citations.py)", url],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        html = out.stdout or ""
    except Exception:  # noqa: BLE001
        return ""
    html = re.sub(r"(?is)<(script|style|head|nav|footer)[^>]*>.*?</\1>", " ", html)
    text = re.sub(r"(?s)<[^>]+>", " ", html)
    text = re.sub(r"&[a-zA-Z#0-9]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


# --------------------------------------------------------------------------- #
# model
# --------------------------------------------------------------------------- #

@dataclass
class ExistenceFinding:
    kind: str          # undefined-citation | broken-source | unverified-source | orphan-source | no-url
    ref: str           # e.g. "[3]"
    line: int
    detail: str = ""


@dataclass
class SupportItem:
    ref: int
    claim: str
    claim_line: int
    source_title: str
    source_url: str
    source_status: str = ""
    source_excerpt: str = ""
    support: str = "NEEDS_LLM_JUDGMENT"   # SUPPORTED|PARTIAL|NOT_SUPPORTED|UNCLEAR|NEEDS_LLM_JUDGMENT
    confidence: str = "n/a"


@dataclass
class UncitedClaim:
    line: int
    sentence: str
    reason: str


@dataclass
class Report:
    path: str
    existence: list[ExistenceFinding] = field(default_factory=list)
    support: list[SupportItem] = field(default_factory=list)
    uncited: list[UncitedClaim] = field(default_factory=list)
    stats: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# uncited-factual-claim heuristic (advisory only)
# --------------------------------------------------------------------------- #

# signals that a sentence is making a checkable factual assertion
FACT_SIGNAL_RE = re.compile(
    r"(\$\s?\d|\b\d+(?:\.\d+)?\s?%|\bper\s+(?:month|hour|second|request|token)\b|"
    r"\bnow\s+(?:supports?|available|offers?|includes?)\b|"
    r"\bis\s+now\s+(?:available|generally\s+available|ga)\b|"
    r"\b(?:launched|released|announced|generally\s+available|\bGA\b)\b|"
    r"\bavailable\s+in\b|\bsupports?\s+up\s+to\b|\bquota\b|\blimit\s+of\b|"
    r"\bversion\s+\d|\bv\d+\.\d+\b|\bx\s+(?:faster|cheaper|more)\b|"
    r"\b\d+(?:,\d{3})+\b)", re.I)
# opinion / first-person framing that does NOT require a citation
OPINION_RE = re.compile(
    r"\b(I\s+think|I\s+believe|in\s+my\s+(?:view|experience|opinion)|"
    r"I\s+(?:wrote|argued|claimed|said|predicted)|we\s+(?:think|believe)|"
    r"arguably|in\s+my\s+head|my\s+take|it\s+feels?\b)", re.I)


def detect_uncited_claims(body: str, raw: str, out: list[UncitedClaim]) -> None:
    # iterate sentences in the body (prose only)
    sentences = re.finditer(r"[^.!?\n]+[.!?](?:\s|$)|[^\n]+(?:\n|$)", body)
    seen_lines: set[int] = set()
    for sm in sentences:
        s = sm.group(0).strip()
        if len(s) < 30:
            continue
        if INLINE_CITE_RE.search(s):
            continue  # already cited
        if OPINION_RE.search(s):
            continue  # first-person opinion — no citation needed
        fact = FACT_SIGNAL_RE.search(s)
        if not fact:
            continue
        ln = line_of(sm.start(), raw)
        if ln in seen_lines:
            continue
        seen_lines.add(ln)
        out.append(UncitedClaim(
            line=ln,
            sentence=re.sub(r"\s+", " ", s)[:200],
            reason=f"factual signal '{fact.group(0).strip()}' but no [N] citation",
        ))


# --------------------------------------------------------------------------- #
# core scan
# --------------------------------------------------------------------------- #

def parse_sources(sources_block: str, block_offset: int, raw: str) -> dict[int, dict]:
    """Map citation number -> {title, url, kind, line}.

    URL precedence: a markdown-link target `](...)` first (handles
    `[label](https://...)` and relative `[label](/blog/...)`), then any bare
    absolute `https://` URL, then any bare relative `/path`. kind is
    'external' (http-checkable) or 'internal' (relative; resolution deferred to
    scripts/check-links.py) or '' (no URL found)."""
    sources: dict[int, dict] = {}
    for m in SOURCE_ENTRY_RE.finditer(sources_block):
        n = int(m.group(1))
        entry = m.group(2).strip()
        url, kind, cut = "", "", len(entry)
        md = MD_TARGET_RE.search(entry)
        abs_m = URL_RE.search(entry)
        rel_m = REL_URL_RE.search(entry)
        if md:
            url = md.group("url")
            kind = "external" if url.startswith("http") else "internal"
            # title is the text before the markdown link label '[...]('
            lab = entry.rfind("[", 0, md.start())
            cut = lab if lab != -1 else md.start()
        elif abs_m:
            url, kind, cut = abs_m.group(0).rstrip(".,);"), "external", abs_m.start()
        elif rel_m:
            url, kind, cut = rel_m.group(1).rstrip(".,);"), "internal", rel_m.start()
        title = re.sub(r"[\s—\-:.,]+$", "", entry[:cut]).strip() or entry[:80]
        sources[n] = {"title": title, "url": url, "kind": kind,
                      "line": line_of(block_offset + m.start(), raw)}
    return sources


def scan_text(raw: str, do_external: bool, do_fetch: bool) -> Report:
    rep = Report(path="<text>")

    nocode = strip_frontmatter(strip_code(raw))
    body, sources_block, sources_off = split_body_sources(nocode)

    sources = parse_sources(sources_block, sources_off if sources_off >= 0 else 0, raw) \
        if sources_block else {}

    # ---- collect inline citations in body (prose where claims live) ----
    cited_numbers: set[int] = set()
    inline_hits: list[tuple[int, int]] = []  # (number, offset)
    for m in INLINE_CITE_RE.finditer(body):
        for part in m.group(1).split(","):
            try:
                n = int(part.strip())
            except ValueError:
                continue
            cited_numbers.add(n)
            inline_hits.append((n, m.start()))

    rep.stats = {
        "inline_citations": len(inline_hits),
        "distinct_cited_refs": len(cited_numbers),
        "sources_defined": len(sources),
    }

    # ---- (1) EXISTENCE ----
    # 1a. inline [N] with no Sources entry
    for n, off in inline_hits:
        if n not in sources:
            rep.existence.append(ExistenceFinding(
                "undefined-citation", f"[{n}]", line_of(off, raw),
                "inline citation has no matching entry in the Sources section"))
    # 1b. Sources entries: URL present + resolves; orphan if never cited
    url_status: dict[int, tuple[str, str]] = {}
    for n, meta in sorted(sources.items()):
        if not meta["url"]:
            rep.existence.append(ExistenceFinding(
                "no-url", f"[{n}]", meta["line"],
                f"source has no URL: {meta['title'][:70]}"))
        elif meta["kind"] == "internal":
            # relative /blog/... — resolution deferred to scripts/check-links.py
            url_status[n] = ("INTERNAL", "relative path (see check-links.py)")
        elif do_external:
            status, detail = check_url(meta["url"])
            url_status[n] = (status, detail)
            if status == "BROKEN":
                rep.existence.append(ExistenceFinding(
                    "broken-source", f"[{n}]", meta["line"],
                    f"{detail}: {meta['url']}"))
            elif status == "UNVERIFIED":
                rep.existence.append(ExistenceFinding(
                    "unverified-source", f"[{n}]", meta["line"],
                    f"{detail}: {meta['url']}"))
        if n not in cited_numbers:
            rep.existence.append(ExistenceFinding(
                "orphan-source", f"[{n}]", meta["line"],
                "defined in Sources but never cited inline"))

    # ---- (2) SUPPORT worklist (one item per distinct claim<->ref pairing) ----
    seen_pairs: set[tuple[int, str]] = set()
    for n, off in inline_hits:
        if n not in sources:
            continue
        claim = sentence_around(body, off)
        key = (n, claim[:60])
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        meta = sources[n]
        status = url_status.get(n, ("", ""))[0]
        excerpt = ""
        if do_fetch and meta["kind"] == "external" and status != "BROKEN":
            excerpt = fetch_excerpt(meta["url"])
        rep.support.append(SupportItem(
            ref=n, claim=claim, claim_line=line_of(off, raw),
            source_title=meta["title"], source_url=meta["url"],
            source_status=status, source_excerpt=excerpt,
        ))

    # ---- (3) uncited factual claims (advisory) ----
    detect_uncited_claims(body, raw, rep.uncited)

    return rep


def scan_file(path: str, do_external: bool, do_fetch: bool) -> Report:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    rep = scan_text(raw, do_external=do_external, do_fetch=do_fetch)
    rep.path = path
    return rep


# --------------------------------------------------------------------------- #
# optional external LLM judge
# --------------------------------------------------------------------------- #

VALID_VERDICTS = {"SUPPORTED", "PARTIAL", "NOT_SUPPORTED", "UNCLEAR"}


def run_judge(item: SupportItem, judge_cmd: str) -> None:
    """Pipe a worklist item to an external LLM command; parse a verdict.
    The command receives the item as JSON on stdin and must print a verdict
    token (SUPPORTED/PARTIAL/NOT_SUPPORTED/UNCLEAR) somewhere on stdout."""
    payload = json.dumps({
        "claim": item.claim,
        "source_title": item.source_title,
        "source_url": item.source_url,
        "source_excerpt": item.source_excerpt,
        "instruction": ("Does the source support the claim ON THE WHOLE (not "
                        "cherry-picked)? Answer with exactly one of: SUPPORTED, "
                        "PARTIAL, NOT_SUPPORTED, UNCLEAR."),
    }, ensure_ascii=False)
    try:
        # judge_cmd is split into an argv (no shell) so quoting/injection semantics
        # are predictable; pass a single executable + args, not a shell pipeline.
        out = subprocess.run(shlex.split(judge_cmd), input=payload,
                             capture_output=True, text=True, timeout=120)
        text = (out.stdout or "").upper()
        for v in VALID_VERDICTS:
            if v in text:
                item.support = v
                item.confidence = "llm-judge (external, advisory)"
                return
        item.support = "UNCLEAR"
        item.confidence = "llm-judge returned no recognizable verdict"
    except Exception as exc:  # noqa: BLE001
        item.support = "UNCLEAR"
        item.confidence = f"judge error: {exc}"


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #

EX_ICON = {
    "undefined-citation": "❌", "broken-source": "❌", "no-url": "❌",
    "unverified-source": "⚠️ ", "orphan-source": "•",
}


def print_human(rep: Report, show_support: bool) -> None:
    print(f"\n=== {rep.path} ===")
    s = rep.stats
    print(f"  citations: {s.get('inline_citations',0)} inline "
          f"({s.get('distinct_cited_refs',0)} distinct) · "
          f"{s.get('sources_defined',0)} sources defined")

    hard = [e for e in rep.existence if e.kind in
            ("undefined-citation", "broken-source", "no-url")]
    soft = [e for e in rep.existence if e.kind == "unverified-source"]
    orph = [e for e in rep.existence if e.kind == "orphan-source"]

    if hard:
        print(f"  ❌ EXISTENCE — {len(hard)} (gate-eligible under --strict)")
        for e in hard:
            print(f"       L{e.line}: [{e.kind}] {e.ref} {e.detail}")
    if soft:
        print(f"  ⚠️  UNVERIFIED SOURCE URLS — {len(soft)} (offline/auth — not failures)")
        for e in soft:
            print(f"       L{e.line}: {e.ref} {e.detail}")
    if orph:
        print(f"  •  ORPHAN SOURCES — {len(orph)} (defined, never cited)")
        for e in orph:
            print(f"       L{e.line}: {e.ref} {e.detail}")
    if not rep.existence:
        print("  ✅ existence: all inline citations resolve to a Sources entry")

    if show_support and rep.support:
        pend = [i for i in rep.support if i.support == "NEEDS_LLM_JUDGMENT"]
        judged = [i for i in rep.support if i.support != "NEEDS_LLM_JUDGMENT"]
        print(f"  ⚖️  CLAIM↔SOURCE SUPPORT — {len(rep.support)} claim/citation pairs")
        if pend:
            print(f"       {len(pend)} NEED LLM JUDGMENT (semantic — see worklist / --json):")
            for i in pend[:8]:
                print(f"         [{i.ref}] L{i.claim_line}: {i.claim[:90]}")
                print(f"               ↳ src: {i.source_title[:70]} ({i.source_status or 'unchecked'})")
            if len(pend) > 8:
                print(f"         … +{len(pend)-8} more (use --json for the full worklist)")
        for i in judged:
            print(f"       [{i.support}] [{i.ref}] L{i.claim_line}: {i.claim[:80]}")

    if rep.uncited:
        print(f"  •  UNCITED FACTUAL CLAIMS (advisory heuristic) — {len(rep.uncited)}")
        for u in rep.uncited[:8]:
            print(f"       L{u.line}: {u.sentence[:90]}")
            print(f"               ↳ {u.reason}")
        if len(rep.uncited) > 8:
            print(f"       … +{len(rep.uncited)-8} more")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Content-pipeline verification gate (existence + support). "
                    "WARN-ONLY by default.")
    ap.add_argument("paths", nargs="+", help="markdown file(s) to verify")
    ap.add_argument("--json", action="store_true", help="machine-readable output (full support worklist)")
    ap.add_argument("--fetch", action="store_true",
                    help="fetch a text excerpt of each source for the support worklist")
    ap.add_argument("--no-external", action="store_true",
                    help="skip URL resolution (offline/headless)")
    ap.add_argument("--strict", action="store_true",
                    help="EXISTENCE failures (undefined citation / broken source) cause exit 1")
    ap.add_argument("--judge-cmd", default="",
                    help="external LLM command to auto-judge support (item JSON on stdin, "
                         "verdict token on stdout); advisory, never affects exit code")
    args = ap.parse_args()

    reports: list[Report] = []
    for path in args.paths:
        try:
            rep = scan_file(path, do_external=not args.no_external, do_fetch=args.fetch)
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 2
        if args.judge_cmd:
            for item in rep.support:
                run_judge(item, args.judge_cmd)
        reports.append(rep)

    # existence failures that are gate-eligible (hard) under --strict
    total_hard = sum(
        len([e for e in r.existence
             if e.kind in ("undefined-citation", "broken-source", "no-url")])
        for r in reports)
    total_support = sum(len(r.support) for r in reports)
    total_uncited = sum(len(r.uncited) for r in reports)

    if args.json:
        payload = {
            "files": [
                {
                    "path": r.path,
                    "stats": r.stats,
                    "existence": [asdict(e) for e in r.existence],
                    "support_worklist": [asdict(i) for i in r.support],
                    "uncited_claims": [asdict(u) for u in r.uncited],
                }
                for r in reports
            ],
            "totals": {
                "existence_hard": total_hard,
                "support_pairs": total_support,
                "uncited_claims": total_uncited,
            },
            "mode": "strict" if args.strict else "warn-only",
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for r in reports:
            print_human(r, show_support=True)
        print("\n" + "=" * 66)
        print(f"Files verified            : {len(reports)}")
        print(f"EXISTENCE failures (hard) : {total_hard}")
        print(f"Support pairs (LLM judge) : {total_support}")
        print(f"Uncited claims (advisory) : {total_uncited}")
        print(f"Mode                      : {'STRICT' if args.strict else 'WARN-ONLY'}")
        print("=" * 66)
        if not args.strict:
            print("RESULT: ⚠️  warn-only — review findings; build NOT blocked.")
            if total_support:
                print("        NOTE: claim↔source SUPPORT needs an LLM judgment pass "
                      "(post-creation Step 11c) — this script only builds the worklist.")
        elif total_hard:
            print("RESULT: ❌ strict — existence failures present.")
        else:
            print("RESULT: ✅ strict — all citations resolve.")

    if args.strict and total_hard:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
