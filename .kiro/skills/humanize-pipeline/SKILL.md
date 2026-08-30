---
name: humanize-pipeline
description: |
  Layered humanization pipeline for blog posts: deterministic AI-smell scan,
  voice-calibrated LLM rewrite (humanizer methodology + the author's calibrated
  voice profile), deterministic re-scan gate, independent-model critique,
  optional detector telemetry. Use when a drafted post needs its AI-writing
  tells removed while keeping the author's voice, facts, and structure intact.
license: Apache-2.0
metadata:
  version: "0.1.0"
---

# Humanize pipeline (layered)

Removes AI-writing tells from a drafted post in five layered stages. The design
rationale in short: mechanical tells go to a regex scanner; cadence, structure
and voice go to a *calibrated* LLM rewrite; substance goes to a **different**
model; detector scores are telemetry at most. The LLM stage can re-introduce
mechanical tells, so the deterministic gate runs after it too.

This skill is the canonical implementation of post-creation **Step 11** — when
both skills are loaded, run Step 11 *through* this pipeline (the scanner run
and the judgment-call category list in post-creation ARE stages 1/3; this
pipeline adds the calibrated rewrite and the independent review).

## Inputs

- `POST.md` — the draft (markdown post with YAML frontmatter).
- Voice profile — resolved via `voice_profile_path` in `config/pipeline.local.json`
  (default: [voice/VOICE.md](voice/VOICE.md)). ALWAYS load it for stage 2.
  **Fill in the template with YOUR corpus before real use** — until then it
  describes the bundled fictional example author.

## Stage 1 — Deterministic pre-pass (fix list)

Run the repo's AI-smell scanner via the helper:

```bash
python3 .kiro/skills/humanize-pipeline/scripts/humanize_check.py pre POST.md --out /tmp/humanize/
```

This runs `scripts/ai_smell_scan.py --json` (repo root; override with
`HUMANIZE_SCANNER=/path/to/ai_smell_scan.py`) and writes `<post>.pre.json`
containing:

- `must_fix` — ARTIFACT findings (chat-tool leakage) + hard-fail SIGNALs
  (`em-dash-excessive`, `ai-vocabulary-strong`, `ai-vocabulary-overused`).
- `should_fix` — remaining SIGNAL findings (negative parallelisms, copula
  avoidance, bold-headers, inline-header lists, ...).
- `info` — STYLE tier (house style; never act on these).

The pre-pass never blocks; its purpose is to hand stage 2 a concrete fix list
instead of letting the LLM re-derive (or miss) the mechanical tells.

## Stage 2 — LLM humanize, ALWAYS voice-calibrated

Apply the humanizer methodology (numbered pattern list, e.g. blader/humanizer
SKILL.md v2.11+, https://raw.githubusercontent.com/blader/humanizer/main/SKILL.md)
with BOTH of:

1. **Voice calibration (mandatory, never run default mode).** Load the voice
   profile and the corpus posts it lists. The profile legitimately overrides
   the humanizer's own style rules where they conflict — e.g. an author who
   naturally uses em dashes at a moderate rate, or conversational pivots that
   default mode would scrub. De-AI'ing into a generic voice is a failure mode,
   not a success.
2. **The stage-1 fix list.** Feed `<post>.pre.json` into the rewrite prompt so
   every `must_fix`/`should_fix` finding is addressed explicitly.

Hard constraints for the rewrite:

- No fabrication: never add a fact, name, number, date, quote, or citation.
- Preserve unchanged: YAML frontmatter, code blocks, link targets, tables, the
  Sources section, and any template shortcodes — EXCEPT human-readable caption
  and alt text, which IS prose and MAY be humanized. Never change link/image
  targets, attributes, or shortcode structure.
- Prose only; keep every claim.
- Verbatim quotes (a researcher's words, a doc excerpt, a customer statement)
  MUST NOT be reworded to satisfy a style rule — see the quote exemption in
  post-creation Step 11.

## Stage 3 — Deterministic post-pass (exit criterion)

```bash
python3 .kiro/skills/humanize-pipeline/scripts/humanize_check.py post REWRITE.md --out /tmp/humanize/
```

Re-runs the scanner on the rewrite. **Exit criterion: no `must_fix` findings**
(scanner hard gate green). This catches what stage 2 re-introduced — a proven
failure mode: adding voice re-imports soft AI vocabulary ("remarkable"-class
words). On FAIL, apply the reported findings and re-run; iterate stages 2↔3 at
most twice before escalating to the user.

## Stage 4 — Independent-model critical read (best-effort)

Run an MCP-free critic agent on the stable rewrite for technical substance
(rigor, citations, overclaiming) — it reviews rigor, not style; keeping it
separate stops the humanizer from "fixing" technical claims.

A sample agent ships at `.kiro/agents/critic.json`. **Model independence is the
point:** invoke it with a `--model` that differs from the model that drafted
the post. A same-model self-review demonstrably misses issues the drafting
model is blind to.

```bash
# MCP-free critic agent; continue-on-fail so a nested-run timeout can NEVER
# abort the pipeline. Replace <other-model> with a model DIFFERENT from the drafter.
timeout 600 kiro-cli chat --agent .kiro/agents/critic.json --no-interactive \
  --model <other-model> --trust-all-tools < REWRITE.md || true
```

**Non-blocking (enforced by `|| true`).** Nested runs can time out; on
timeout/error, log the outcome and continue — but NEVER silently substitute a
same-model review and present it as if the independent gate passed (see the
independent-review rule in `writing-guardrails.md`). For posts whose primary
subject is a product launch or technical-rigor content, treat a failed gate as
"NOT SATISFIED — needs an interactive re-run", surfaced as a headline in your
run report.

## Stage 5 — Detector score (advisory telemetry only)

If a free/local AI-text detector is available, log its score as telemetry next
to the fix-list JSONs. **Never edit the text to move the score** — optimizing
the proxy degrades the prose, and the score goes stale with every model
generation. If no detector is practical in your environment, skip and note
"skipped" in the run log.

## Helper: scripts/humanize_check.py

- `pre FILE` — stage-1 scan, writes `<stem>.pre.json`, prints criterion status
  (informational, always exits 0).
- `post FILE` — stage-3 scan, writes `<stem>.post.json`, prints `PASS`/`FAIL`,
  exits 1 on FAIL.
- `--self-test` — runs a built-in fixture check (clean text passes, seeded
  artifact + strong-vocab text fails).

Stdlib-only; no install needed.

## Voice profile

`voice/VOICE.md` is a fill-in template: your public writing corpus (URLs or
paths), 5–8 extracted voice traits at calibratable granularity, and any
explicit overrides of humanizer rules. Ships pre-filled for the bundled
fictional example author so a fresh clone runs end-to-end. Point
`voice_profile_path` in `config/pipeline.local.json` at your own copy. Public
content only — never include private drafts or PII.
