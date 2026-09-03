#!/usr/bin/env python3
"""
ai_smell_scan.py — deterministic AI-smell scanner for blog drafts and posts.

This is the *mechanical* half of the AI smell check. It covers the
regex-detectable "Signs of AI writing"
(https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing) so they cannot be
silently skipped by an LLM grading its own output. Judgment calls (tone,
significance inflation, hollow conclusions, voice) stay in the LLM prose pass —
see post-creation Step 11.

Design principle (from 06-knowledge/tools/ai-smell-check-improvements.md):
mechanical tells -> a script; semantic tells -> the LLM pass. The script never
tries to do the LLM's job and the LLM never has to count em-dashes by eye.

SEVERITY TIERS
--------------
  ARTIFACT  Near-deterministic AI leakage — citation-markup junk pasted from a
            chat tool (utm_source=chatgpt.com, turn0search0, :contentReference,
            oaicite, grok_card, placeholder dates, [Your Name] ...).
            There is no legitimate reason for these in a finished post.
            -> ALWAYS causes a non-zero exit (the hard gate).

  SIGNAL    Real AI stylistic tells with low-to-moderate false-positive rate:
            negative parallelisms ("not just X, but Y"), copula avoidance
            ("serves as" instead of "is"), "Challenges / Future prospects"
            outline conclusions, bold-sentence headers, inline-header lists,
            em-dash overuse, banned AI vocabulary.
            -> Most are reported for human/LLM review and fail only with --strict.
               EXCEPT (hard-fail by default, calibrated to the author's voice —
               user policy 2026-06-06):
                 * em-dash-excessive    : em-dash rate > 18/1000 words
                 * ai-vocabulary-strong : a strong AI-tell word (delve, tapestry,
                                          showcase, underscore, pivotal, ...)
                 * ai-vocabulary-overused: a softer AI-leaning word repeated >= 3x
               (A flat em-dash count > 10 within the author's normal rate, and a
               single common AI-leaning word, stay advisory.)

  STYLE     Weak signals or this author's established house style: curly quotes
            (macOS smart-quotes / Hugo typographer produce these), Title Case
            headings (the author writes headings in Title Case deliberately),
            skipped heading levels, and prose-rhythm statistics.
            -> Informational only. NEVER affects the exit code. Suppress with
               --no-style.

Why the tiering matters: run over this author's existing, hand-edited posts the
gate must stay GREEN (no false positives), while a draft containing pasted
ChatGPT citation markup must go RED. Curly quotes and Title Case headings are
this author's norm, so they are reported as STYLE, not asserted as "AI".

USAGE
-----
    python3 ai_smell_scan.py POST.md [MORE.md ...]
    python3 ai_smell_scan.py --json POST.md          # machine-readable
    python3 ai_smell_scan.py --strict POST.md        # SIGNALs also fail
    python3 ai_smell_scan.py --no-style POST.md      # hide STYLE/INFO section
    python3 ai_smell_scan.py --comment NOTE.md       # comment/short-text mode

EXIT CODES
----------
    0  no ARTIFACT, no hard-fail SIGNAL (em-dash-excessive / ai-vocabulary-strong
       / ai-vocabulary-overused), and — under --strict — no SIGNAL findings
    1  ARTIFACT, OR a hard-fail SIGNAL, OR (under --strict) any SIGNAL finding
    2  usage / file error

Detection-only by design (the task is *detection*). It never rewrites files,
so it cannot corrupt the author's intentional typography.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from dataclasses import dataclass, field, asdict
from typing import Optional

# --------------------------------------------------------------------------- #
# code / structure stripping (line numbers preserved by blanking, not deleting)
# --------------------------------------------------------------------------- #

FENCE_RE = re.compile(r"(^|\n)(```|~~~).*?(\n)(?:.*?\n)??\2[ \t]*(?=\n|$)", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
FRONTMATTER_RE = re.compile(r"\A---\n.*?\n---[ \t]*(?=\n|$)", re.DOTALL)
SOURCES_HEADING_RE = re.compile(r"^#{1,6}\s+sources\b.*$", re.IGNORECASE | re.MULTILINE)


def _blank(m: re.Match) -> str:
    """Replace a span with spaces/newlines so offsets & line numbers survive."""
    return re.sub(r"[^\n]", " ", m.group(0))


def strip_code(text: str) -> str:
    text = FENCE_RE.sub(_blank, text)
    text = INLINE_CODE_RE.sub(_blank, text)
    return text


def strip_frontmatter(text: str) -> str:
    return FRONTMATTER_RE.sub(_blank, text)


def strip_sources(text: str) -> str:
    """Blank from the 'Sources'/'References' heading to EOF (reference list,
    not prose). Used for prose-only checks (vocab, rhythm, parallelisms)."""
    m = SOURCES_HEADING_RE.search(text)
    if not m:
        return text
    head = text[: m.start()]
    tail = re.sub(r"[^\n]", " ", text[m.start():])
    return head + tail


def line_of(offset: int, text: str) -> int:
    return text.count("\n", 0, offset) + 1


# --------------------------------------------------------------------------- #
# finding model
# --------------------------------------------------------------------------- #

ARTIFACT, SIGNAL, STYLE = "ARTIFACT", "SIGNAL", "STYLE"

# SIGNAL categories promoted to HARD-FAIL by default (user policy, 2026-06-06,
# calibrated against the author's real em-dash/vocab distribution so the gate is
# red only on GENUINE overuse, not the author's normal voice):
#   - em-dash-excessive   : rate > EMDASH_HARD_RATE /1000w (top ~decile)
#   - ai-vocabulary-strong: a strong AI-tell word (delve, tapestry, showcase ...)
#   - ai-vocabulary-overused: a softer banned word repeated >= VOCAB_REPEAT_HARD x
# The advisory siblings (em-dash-overuse count>10, single soft ai-vocabulary hit)
# stay review-only (fail only under --strict).
HARD_FAIL_CATEGORIES = {"em-dash-excessive", "ai-vocabulary-strong",
                        "ai-vocabulary-overused"}


@dataclass
class Finding:
    tier: str
    category: str
    line: int
    snippet: str
    note: str = ""


@dataclass
class FileReport:
    path: str
    findings: list[Finding] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def by_tier(self, tier: str) -> list[Finding]:
        return [f for f in self.findings if f.tier == tier]


# --------------------------------------------------------------------------- #
# pattern banks
# --------------------------------------------------------------------------- #

# 1) ARTIFACT — citation-markup / chat-tool leakage (run on full doc minus code)
ARTIFACT_PATTERNS: list[tuple[str, re.Pattern, str]] = [
    ("utm-source-ai", re.compile(r"utm_source=(?:chatgpt(?:\.com)?|openai)", re.I),
     "URL tracking param from ChatGPT/OpenAI — paste leftover"),
    ("referrer-grok", re.compile(r"referrer=grok\.com", re.I),
     "Grok referrer param — paste leftover"),
    ("turn-search", re.compile(r"\bturn\d+(?:search|image|news|file|view|forecast)\d+\b", re.I),
     "OpenAI search-tool citation token (e.g. turn0search0)"),
    ("oaicite", re.compile(r":?contentReference|oaicite|oai_citation", re.I),
     "OpenAI inline-citation markup artifact"),
    ("grok-card", re.compile(r"grok_card", re.I),
     "Grok card markup artifact"),
    ("citation-glyph", re.compile(r"【\d+†"),
     "Citation-bug glyph (【N†...】)"),
    ("placeholder-date", re.compile(r"\b20\d\d-[xX]{2}-[xX]{2}\b|\b[xX]{4}-[xX]{2}-[xX]{2}\b"),
     "Unfilled placeholder date (YYYY-XX-XX)"),
    ("bracket-placeholder",
     re.compile(r"\[(?:your name|insert[^\]]*|paste[^\]]*|todo|placeholder|tk)\]", re.I),
     "Unfilled bracket placeholder"),
]

# 2) SIGNAL — negative parallelisms
NEG_PARALLEL_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("not just X, but Y", re.compile(r"\bnot\s+just\b[^,.;:]{1,70},\s+but\b", re.I)),
    ("not only X, but Y", re.compile(r"\bnot\s+only\b[^,.;:]{1,70},\s+but\b", re.I)),
    ("it's not X, it's Y",
     re.compile(r"\bit['\u2019]s\s+not\b[^,.;:]{1,60}[,.]\s+it['\u2019]s\b", re.I)),
    ("not X, but rather Y",
     re.compile(r"\bnot\b[^,.;:]{1,50},\s+but\s+(?:rather|instead)\b", re.I)),
]

# 3) SIGNAL — copula avoidance (high-signal verbs only; "features/offers" excluded
#    as too noisy -> left to the LLM pass)
COPULA_RE = re.compile(
    r"\b(serves as|stands as|acts as|functions as|positions itself as|"
    r"represents (?:a|an|the)\b|boasts\b|showcases\b)", re.I)

# 3b) SIGNAL — summary-frame / distancing constructions.
# "The argument was that X" states X at arm's length instead of just stating X. It is the
# written equivalent of introducing yourself in the third person, and it shows up constantly
# in LLM prose when summarizing a prior point, a source, or the writer's own earlier work.
# The fix is nearly always to delete the frame and assert the claim directly:
#     "The argument was that the clip matters."  ->  "The clip matters."
#     "What I found was that it crackled."       ->  "It crackled."
# Deliberately NOT matched: "the argument that X is wrong" (referring to an argument as an
# object is fine), and question forms ("what the argument was" in reported speech).
SUMMARY_FRAME_RE = re.compile(
    r"\b(?:"
    r"the\s+(?:argument|point|idea|thesis|premise|takeaway|lesson|insight|claim|upshot|"
    r"conclusion|reasoning|observation|finding|realization|realisation)\s+"
    r"(?:was|is|here\s+was|here\s+is|being)\s+(?:that|this)\b"
    r"|what\s+(?:I|we)\s+(?:found|learned|discovered|realized|realised)\s+was\s+that\b"
    r"|the\s+(?:key|main|whole)\s+(?:point|idea|insight)\s+(?:was|is)\s+that\b"
    r")", re.I)

# 5) SIGNAL — "Challenges / Future" outline conclusions
CHALLENGES_HEADING_RE = re.compile(
    r"^#{1,6}\s+.*\b("
    r"challenges?(?:\s+and|\s*&)?\s+(?:future|outlook|prospects?|considerations?)|"
    r"future\s+(?:prospects?|directions?|outlook|of)|"
    r"looking\s+ahead|the\s+road\s+ahead|what['\u2019]?s?\s+next"
    r")\b.*$", re.I | re.M)
DESPITE_FORMULA_RE = re.compile(
    r"\bdespite\s+(?:its|the|these|their|significant)\b[^,.\n]{1,70},"
    r"[^.\n]{0,50}\b(faces?|remains?|challenges?|hurdles?|obstacles?|concerns?)\b", re.I)
ONLY_TIME_RE = re.compile(r"\bonly time will tell\b", re.I)

# 7) SIGNAL — bold-sentence headers and inline-header lists
BOLD_SENTENCE_HEADER_RE = re.compile(r"^\s{0,3}\*\*[^*\n]+[.:!?]\*\*\s+\S", re.M)
INLINE_HEADER_LIST_RE = re.compile(r"^\s*[-*+]\s+\*\*[^*\n]{1,50}:\*\*\s+\S", re.M)

# 8) em dashes
EMDASH_RE = re.compile(r"\u2014")
EMDASH_THRESHOLD = 10      # advisory: count per post (em-dash-overuse, review-only)
EMDASH_HARD_RATE = 18.0    # hard-fail: rate per 1000 words (calibrated > author p90
                           # ≈ 19.6; median is 3.2 — genuine overuse only)

# 9) banned AI vocabulary (Step 11 list + era-drift additions from P1.2)
# Split into STRONG tells (hard-fail on a single hit) vs SOFT common words
# (advisory on a single hit; hard-fail only when repeated >= VOCAB_REPEAT_HARD).
STRONG_VOCAB = [
    "delve", "tapestry", "seamlessly", "groundbreaking", "paradigm", "holistic",
    "intricate", "cornerstone", "testament", "underscore", "pivotal", "vibrant",
    "showcase", "showcasing", "emphasizing", "highlighting", "elevate",
]
SOFT_VOCAB = [
    "landscape", "leverage", "robust", "facilitate", "comprehensive",
    "straightforward", "fascinating", "remarkable", "nuanced", "navigate",
]
STRONG_VOCAB_SET = {w.lower() for w in STRONG_VOCAB}
VOCAB_REPEAT_HARD = 3      # a soft word repeated this many times hard-fails
BANNED_VOCAB = STRONG_VOCAB + SOFT_VOCAB
BANNED_VOCAB_RE = re.compile(
    r"\b(" + "|".join(re.escape(w) for w in BANNED_VOCAB) + r")\b", re.I)

# 4/6/10) STYLE — headings, curly quotes
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$", re.M)
CURLY_DOUBLE_RE = re.compile(r"[\u201c\u201d]")
CURLY_SINGLE_RE = re.compile(r"[\u2018\u2019]")
# minor words that should be lowercase in sentence case -> capitalized mid-heading
# is a strong Title-Case indicator (low false-positive vs proper-noun headings)
MINOR_WORDS = {
    "a", "an", "the", "and", "or", "but", "nor", "of", "to", "in", "on", "at",
    "for", "with", "as", "by", "from", "vs", "than", "that", "this", "is",
    "are", "be", "it", "its", "into", "over", "up", "out", "if", "so", "yet",
}


# --------------------------------------------------------------------------- #
# detectors
# --------------------------------------------------------------------------- #

def detect_artifacts(full_nocode: str, raw: str, out: list[Finding]) -> None:
    for cat, pat, note in ARTIFACT_PATTERNS:
        for m in pat.finditer(full_nocode):
            out.append(Finding(ARTIFACT, cat, line_of(m.start(), raw),
                               _ctx(raw, m.start(), m.end()), note))


def detect_negative_parallelisms(prose: str, raw: str, out: list[Finding]) -> None:
    for label, pat in NEG_PARALLEL_PATTERNS:
        for m in pat.finditer(prose):
            out.append(Finding(SIGNAL, "negative-parallelism",
                               line_of(m.start(), raw), m.group(0).strip(),
                               f"pattern: {label}"))


def detect_copula_avoidance(prose: str, raw: str, out: list[Finding]) -> None:
    for m in COPULA_RE.finditer(prose):
        out.append(Finding(SIGNAL, "copula-avoidance", line_of(m.start(), raw),
                           _ctx(raw, m.start(), m.end()),
                           "prefer a plain 'is/are/has' where it reads better"))


def detect_summary_frame(prose: str, raw: str, out: list[Finding]) -> None:
    """Flag 'The argument was that X' style frames — state X directly instead."""
    for m in SUMMARY_FRAME_RE.finditer(prose):
        out.append(Finding(SIGNAL, "summary-frame", line_of(m.start(), raw),
                           _ctx(raw, m.start(), m.end()),
                           "drop the frame and assert the claim directly "
                           "('The argument was that the clip matters' -> 'The clip matters')"))


def detect_challenges_conclusion(prose: str, raw: str, out: list[Finding]) -> None:
    for m in CHALLENGES_HEADING_RE.finditer(prose):
        out.append(Finding(SIGNAL, "challenges-future-outline",
                           line_of(m.start(), raw), m.group(0).strip(),
                           "outline-style 'Challenges/Future' conclusion heading"))
    for m in DESPITE_FORMULA_RE.finditer(prose):
        out.append(Finding(SIGNAL, "challenges-future-outline",
                           line_of(m.start(), raw), m.group(0).strip(),
                           "'Despite its X, faces challenges' formula"))
    for m in ONLY_TIME_RE.finditer(prose):
        out.append(Finding(SIGNAL, "challenges-future-outline",
                           line_of(m.start(), raw), m.group(0).strip(),
                           "'only time will tell' filler conclusion"))


def detect_bold_headers(full_nocode: str, raw: str, out: list[Finding]) -> None:
    for m in BOLD_SENTENCE_HEADER_RE.finditer(full_nocode):
        out.append(Finding(SIGNAL, "bold-sentence-header",
                           line_of(m.start(), raw), m.group(0).strip()[:80],
                           "**Phrase.** Rest... — restructure as prose or ### heading"))
    for m in INLINE_HEADER_LIST_RE.finditer(full_nocode):
        out.append(Finding(SIGNAL, "inline-header-list",
                           line_of(m.start(), raw), m.group(0).strip()[:80],
                           "- **Header:** text — AI list tell in prose"))


def detect_emdash(prose: str, raw: str, words: int, out: list[Finding],
                  stats: dict) -> None:
    hits = list(EMDASH_RE.finditer(prose))
    stats["em_dashes"] = len(hits)
    rate = round(len(hits) / max(words, 1) * 1000, 1)
    stats["em_dash_per_1000w"] = rate
    if not hits:
        return
    first = hits[0]
    if rate > EMDASH_HARD_RATE:
        out.append(Finding(SIGNAL, "em-dash-excessive", line_of(first.start(), raw),
                           f"{len(hits)} em dashes in prose ({rate}/1000 words)",
                           f"HARD-FAIL: rate > {EMDASH_HARD_RATE}/1000w (genuine "
                           f"overuse vs author median 3.2) — replace excess with , . : ()"))
    elif len(hits) > EMDASH_THRESHOLD:
        out.append(Finding(SIGNAL, "em-dash-overuse", line_of(first.start(), raw),
                           f"{len(hits)} em dashes in prose ({rate}/1000 words)",
                           f"advisory: count > {EMDASH_THRESHOLD} but rate "
                           f"<= {EMDASH_HARD_RATE}/1000w (within author's normal range)"))


def detect_banned_vocab(prose: str, raw: str, out: list[Finding],
                        stats: dict) -> None:
    counts: dict[str, int] = {}
    for m in BANNED_VOCAB_RE.finditer(prose):
        w = m.group(0).lower()
        counts[w] = counts.get(w, 0) + 1
        if w in STRONG_VOCAB_SET:
            out.append(Finding(SIGNAL, "ai-vocabulary-strong", line_of(m.start(), raw),
                               _ctx(raw, m.start(), m.end()),
                               f"HARD-FAIL: strong AI-tell word '{w}'"))
        else:
            out.append(Finding(SIGNAL, "ai-vocabulary", line_of(m.start(), raw),
                               _ctx(raw, m.start(), m.end()),
                               f"advisory: common AI-leaning word '{w}'"))
    # a softer banned word relied on heavily (>= VOCAB_REPEAT_HARD) hard-fails
    for w, c in counts.items():
        if w not in STRONG_VOCAB_SET and c >= VOCAB_REPEAT_HARD:
            out.append(Finding(SIGNAL, "ai-vocabulary-overused", 0,
                               f"'{w}' x{c}",
                               f"HARD-FAIL: AI-leaning word repeated {c}x "
                               f"(>= {VOCAB_REPEAT_HARD})"))
    stats["ai_vocab_counts"] = counts


def detect_curly_quotes(full_nocode: str, out: list[Finding], stats: dict) -> None:
    d = len(CURLY_DOUBLE_RE.findall(full_nocode))
    s = len(CURLY_SINGLE_RE.findall(full_nocode))
    stats["curly_double"] = d
    stats["curly_single"] = s
    if d or s:
        out.append(Finding(
            STYLE, "curly-quotes", 0,
            f'curly double=" "×{d}, single/apostrophe=\u2018 \u2019×{s}',
            "macOS smart-quotes / Hugo typographer also produce these — "
            "weak AI signal for this author; verify, do not auto-straighten"))


def detect_headings(full_nocode: str, raw: str, out: list[Finding],
                    stats: dict) -> None:
    levels: list[tuple[int, int]] = []  # (line, level)
    title_case = 0
    for m in HEADING_RE.finditer(full_nocode):
        level = len(m.group(1))
        text = m.group(2).strip()
        ln = line_of(m.start(), raw)
        levels.append((ln, level))
        words = re.findall(r"[A-Za-z][A-Za-z'\u2019]*", text)
        # Title Case tell: a minor word capitalized somewhere other than 1st word
        for i, w in enumerate(words):
            if i == 0:
                continue
            if w.lower() in MINOR_WORDS and w[0].isupper():
                title_case += 1
                out.append(Finding(
                    STYLE, "title-case-heading", ln, text[:80],
                    "capitalized minor word mid-heading — likely the author's "
                    "Title Case house style, not necessarily AI"))
                break
    stats["title_case_headings"] = title_case
    # skipped heading levels (e.g. h2 -> h4)
    prev = 0
    for ln, level in levels:
        if prev and level > prev + 1:
            out.append(Finding(STYLE, "skipped-heading-level", ln,
                               f"h{prev} -> h{level}",
                               "heading level skipped"))
        prev = level


def compute_rhythm(prose: str, stats: dict) -> int:
    # words
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'\u2019\-]*", prose)
    stats["words"] = len(words)
    # sentences (rough: split on . ! ? followed by space/newline)
    sentences = [s for s in re.split(r"(?<=[.!?])\s+", prose) if s.strip()]
    slens = [len(re.findall(r"\w+", s)) for s in sentences if re.findall(r"\w+", s)]
    if slens:
        stats["sentence_count"] = len(slens)
        stats["sentence_len_mean"] = round(statistics.mean(slens), 1)
        stats["sentence_len_stdev"] = round(
            statistics.pstdev(slens) if len(slens) > 1 else 0.0, 1)
    # paragraphs (blank-line separated, non-empty)
    paras = [p for p in re.split(r"\n\s*\n", prose) if p.strip()]
    plens = [len(re.findall(r"\w+", p)) for p in paras if re.findall(r"\w+", p)]
    if plens:
        stats["paragraph_count"] = len(plens)
        stats["paragraph_len_mean"] = round(statistics.mean(plens), 1)
        stats["paragraph_len_stdev"] = round(
            statistics.pstdev(plens) if len(plens) > 1 else 0.0, 1)
    return len(words)


def _ctx(raw: str, start: int, end: int, pad: int = 24) -> str:
    a = max(0, start - pad)
    b = min(len(raw), end + pad)
    snip = raw[a:b].replace("\n", " ").strip()
    return ("…" if a > 0 else "") + snip + ("…" if b < len(raw) else "")


# --------------------------------------------------------------------------- #
# per-file scan
# --------------------------------------------------------------------------- #

def scan_text(raw: str, comment_mode: bool = False) -> FileReport:
    rep = FileReport(path="<text>")

    nocode = strip_code(raw)
    full_nocode = strip_frontmatter(nocode)            # artifacts/headings/curly
    prose = strip_sources(full_nocode)                 # vocab/rhythm/parallelisms

    findings: list[Finding] = []
    stats: dict = {}

    # ARTIFACT (hard) — scan full doc minus code (incl. Sources & frontmatter URLs)
    detect_artifacts(nocode, raw, findings)

    # SIGNAL
    detect_negative_parallelisms(prose, raw, findings)
    detect_copula_avoidance(prose, raw, findings)
    detect_summary_frame(prose, raw, findings)
    detect_challenges_conclusion(prose, raw, findings)
    detect_bold_headers(full_nocode, raw, findings)
    words = compute_rhythm(prose, stats)
    detect_emdash(prose, raw, words, findings, stats)
    detect_banned_vocab(prose, raw, findings, stats)

    # STYLE / INFO
    detect_curly_quotes(full_nocode, findings, stats)
    if not comment_mode:
        detect_headings(full_nocode, raw, findings, stats)

    rep.findings = findings
    rep.stats = stats
    return rep


def scan_file(path: str, comment_mode: bool = False) -> FileReport:
    with open(path, encoding="utf-8") as fh:
        raw = fh.read()
    rep = scan_text(raw, comment_mode=comment_mode)
    rep.path = path
    return rep


# --------------------------------------------------------------------------- #
# reporting
# --------------------------------------------------------------------------- #

TIER_ICON = {ARTIFACT: "❌", SIGNAL: "⚠️ ", STYLE: "•"}


def print_human(rep: FileReport, show_style: bool) -> None:
    print(f"\n=== {rep.path} ===")
    arts = rep.by_tier(ARTIFACT)
    sigs = rep.by_tier(SIGNAL)
    stys = rep.by_tier(STYLE)

    if arts:
        print(f"  ❌ ARTIFACT (hard gate) — {len(arts)}")
        for f in arts:
            print(f"       L{f.line}: [{f.category}] {f.snippet}")
            if f.note:
                print(f"               ↳ {f.note}")

    if sigs:
        # group by category for a compact view
        by_cat: dict[str, list[Finding]] = {}
        for f in sigs:
            by_cat.setdefault(f.category, []).append(f)
        print(f"  ⚠️  SIGNAL (review) — {len(sigs)}")
        for cat, items in sorted(by_cat.items()):
            blk = "  ❌ HARD-FAIL" if cat in HARD_FAIL_CATEGORIES else ""
            print(f"       {cat}: {len(items)}{blk}")
            for f in items[:6]:
                print(f"         L{f.line}: {f.snippet}")
            if len(items) > 6:
                print(f"         … +{len(items) - 6} more")

    if show_style and stys:
        print(f"  •  STYLE / INFO (house-style / weak signal — never fails) — {len(stys)}")
        for f in stys:
            loc = f"L{f.line}" if f.line else "—"
            print(f"       {loc}: [{f.category}] {f.snippet}")

    s = rep.stats
    if s:
        bits = []
        if "words" in s:
            bits.append(f"words={s['words']}")
        if "em_dashes" in s:
            bits.append(f"em-dashes={s['em_dashes']} ({s.get('em_dash_per_1000w',0)}/1k)")
        if "sentence_len_mean" in s:
            bits.append(f"sent μ={s['sentence_len_mean']}±{s.get('sentence_len_stdev',0)}")
        if "paragraph_len_mean" in s:
            bits.append(f"para μ={s['paragraph_len_mean']}±{s.get('paragraph_len_stdev',0)}")
        if bits:
            print("       stats: " + ", ".join(bits))

    if not arts and not sigs and not (show_style and stys):
        print("  ✅ clean (no artifacts, no signals)")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic AI-smell scanner (mechanical tells only).")
    ap.add_argument("paths", nargs="+", help="markdown file(s) to scan")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--strict", action="store_true",
                    help="SIGNAL findings also cause a non-zero exit")
    ap.add_argument("--no-style", action="store_true",
                    help="hide STYLE/INFO findings (curly quotes, Title Case ...)")
    ap.add_argument("--comment", action="store_true",
                    help="comment/short-text mode (skip heading checks)")
    args = ap.parse_args()

    reports: list[FileReport] = []
    for path in args.paths:
        try:
            reports.append(scan_file(path, comment_mode=args.comment))
        except OSError as exc:
            print(f"error: cannot read {path}: {exc}", file=sys.stderr)
            return 2

    total_art = sum(len(r.by_tier(ARTIFACT)) for r in reports)
    total_sig = sum(len(r.by_tier(SIGNAL)) for r in reports)
    total_sty = sum(len(r.by_tier(STYLE)) for r in reports)
    total_hard_sig = sum(1 for r in reports for f in r.findings
                         if f.category in HARD_FAIL_CATEGORIES)

    if args.json:
        payload = {
            "files": [
                {
                    "path": r.path,
                    "findings": [asdict(f) for f in r.findings
                                 if not (args.no_style and f.tier == STYLE)],
                    "stats": r.stats,
                    "counts": {
                        "artifact": len(r.by_tier(ARTIFACT)),
                        "signal": len(r.by_tier(SIGNAL)),
                        "style": len(r.by_tier(STYLE)),
                    },
                }
                for r in reports
            ],
            "totals": {"artifact": total_art, "signal": total_sig, "style": total_sty},
            "strict": args.strict,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        for r in reports:
            print_human(r, show_style=not args.no_style)
        print("\n" + "=" * 64)
        print(f"Files scanned : {len(reports)}")
        print(f"ARTIFACT (hard gate) : {total_art}")
        print(f"SIGNAL (review)      : {total_sig}")
        print(f"STYLE (info)         : {total_sty}")
        print("=" * 64)

    fail = total_art > 0 or total_hard_sig > 0 or (args.strict and total_sig > 0)
    if not args.json:
        if fail:
            reasons = []
            if total_art:
                reasons.append("ARTIFACT")
            if total_hard_sig:
                reasons.append("em-dash/vocab (hard SIGNAL)")
            if args.strict and total_sig > total_hard_sig:
                reasons.append("other SIGNAL (--strict)")
            print(f"RESULT: ❌ {', '.join(reasons)} findings — fix before publishing")
        else:
            print("RESULT: ✅ no hard-gate findings")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
