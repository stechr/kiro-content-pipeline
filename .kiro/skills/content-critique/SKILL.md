---
name: content-critique
description: Independent outside review of a complete content item — critiques BOTH the outcome (quality + correctness of the post, images, and intermediate artifacts) AND the process that produced it, with out-of-the-box improvement proposals (extra pipeline steps, methodology, different models, tooling). Use when the user says "content critique", "critique this post/item", "outside review", "review the content item", or "critique the pipeline". Run it on a DIFFERENT model than the one that drafted, MCP-free.
requires:
  steering: [ground-truth.md, writing-guardrails.md, pre-publish-safety.md]
---

# Content Critique

## Overview

A rigorous, independent **outside reviewer** for a whole content item. Unlike the per-step
quality gates baked into `post-creation` (ai-smell, claim-verification, visual-qa) and unlike
the narrow critic agent (a technical-rigor pass on the post *text* only — `.kiro/agents/critic.json`),
this skill reviews the **entire artifact set together** and — crucially — also critiques the
**process** that produced it and proposes improvements, including out-of-the-box ideas.

For real independence, run it **headless on a model different from the one that drafted the
item** (see Invocation). It MUST NOT rubber-stamp the existing gate reports — it treats them
as claims to challenge.

## Relationship to existing gates (do not duplicate blindly)

- Critic agent (`.kiro/agents/critic.json`) — narrow: technical rigor of the post text on a
  *different* model. Keep it; this skill is broader.
- `post-creation` gates — per-artifact, deterministic + LLM (ai-smell, claim-verification,
  visual-qa). This skill re-examines their *outputs* skeptically and adds cross-artifact +
  process critique they cannot see.

## Parameters

- **item** (required): the content-item identifier — a `<date>-<slug>` (resolved via
  `scripts/content_paths.py item-dir <date>-<slug>`) or an absolute item-root path.
- **scope** (optional): `outcome` | `process` | `both`. Defaults to `both`.

## Workflow

### 1. Resolve the item root and enumerate ALL artifacts

Locate the content-item root and build a complete inventory before reading.

**Constraints:**
- You MUST resolve the item root with `python3 scripts/content_paths.py item-dir <date>-<slug>`
  because every artifact path derives from it.
- You MUST enumerate the full artifact set (a directory listing at depth 2 of the item root),
  not assume a fixed list, because items vary (some have no `ideation.md`, some carry extra
  derivative artifacts from downstream pipelines).
- You MUST record which artifacts are present vs absent, because an absent required artifact
  (e.g. missing `faq.md` or `claim-verification.md`) is itself a PROCESS finding.

**Grounded artifact map (this pipeline's scope — ideation → final draft):**

| Artifact | Path (under item root) | What it is |
|---|---|---|
| Blog post | `blog/post.md` | the primary outcome |
| FAQ | `faq.md` | reader-aid Q&A |
| Challenging questions | `challenging-questions.md` | critical-reader Q&A |
| Ideation (DoR) | `ideation.md` | the finalized thesis/scope/claim-ledger (if present) |
| Image prompts | `image-prompts.md` | proposed visuals |
| AI-smell report | `ai-smell.md` | style gate output |
| Claim/leak verification | `claim-verification.md` | substance + leak gate output |
| Visual QA | `visual-qa.md` | image/figure gate output |
| Images / diagrams | `assets/*` | cover, diagrams (if generated) |
| Manifest | `content-item.md` | item status/metadata |

Downstream derivative artifacts (teasers, videos, platform posts) produced by OTHER pipelines
may sit in the same folder — note their presence and include them in cross-artifact checks
when present, but their absence is not a finding here.

### 2. Read the artifacts (honest depth)

Read each present artifact in full; read images via the image-read tool.

**Constraints:**
- You MUST read `blog/post.md`, `faq.md`, `challenging-questions.md`, and every present gate
  report in full, because these are the shipped outcome and its evidence.
- You MUST read images downscaled to ≤1400px max dimension, ≤4 per request, because
  larger/batched images exceed multi-image request limits and fail the turn.
- You MUST NOT claim to have reviewed any artifact you could not open — state it, because
  implying depth you don't have is a depth-honesty violation (`ground-truth.md`).
- You MUST state, in the report, which artifacts you read in full vs skimmed vs could not access.

### 3. OUTCOME review — quality + correctness

Judge the finished artifacts independently; challenge the existing gate reports.

**Constraints:**
- You MUST verify every load-bearing technical/product claim against a fetched authoritative
  source in the same pass (`web_fetch`/`web_search`), because asserting correctness from model
  memory violates `ground-truth.md`. Honor the trust hierarchy (official docs first).
- Any "Verified" verdict you issue MUST carry a verbatim short quote from the fetched source —
  a verdict without a quote is Unverified (see post-creation's quoted-excerpt rule).
- You MUST NOT treat the existing `ai-smell.md`/`claim-verification.md`/`visual-qa.md` as
  authoritative — re-derive independently and flag where they missed something, because the
  whole point of an outside pass is to catch what the in-pipeline gates did not.
- You MUST check, at minimum: leak / PII / internal-marker exposure (run `scripts/leak_scan.py`
  yourself); third-party branding and competitor framing per `writing-guardrails.md`;
  fabricated first-person claims; public links resolve and use production domains (no
  localhost/preview URLs); date/day-of-week correctness; image alt-text; and code-snippet
  safety per `pre-publish-safety.md`.
- You MUST perform a CROSS-ARTIFACT consistency check: FAQ vs post, ideation thesis vs shipped
  post (thesis drift), image prompts vs the post's argument — because per-artifact gates cannot
  see drift between artifacts.
- You SHOULD assess craft-level quality too (structure, clarity, hook, pacing, voice
  consistency with the configured style corpus) and not only defects.

### 4. PROCESS review — pipeline critique + improvement proposals

Critique the pipeline that produced these artifacts and propose improvements.

**Constraints:**
- You MUST identify concrete process weaknesses evidenced by the artifacts (missing/empty
  required artifacts, a gate that ran but missed a defect you found in Step 3, wrong ordering,
  redundant steps, weak coverage), because process findings must be grounded in observed
  evidence, not generic advice.
- You MUST include out-of-the-box improvement PROPOSALS: additional pipeline steps, methodology
  changes, using a different model for a specific step, new tooling/automation, or stronger
  gates — and you MUST label each clearly as a proposal (not a defect), because proposals and
  defects have different urgency.
- You SHOULD tie each process proposal to a specific finding or artifact it would have
  caught/improved, because untethered suggestions are low-value.
- You MUST NOT recommend adding a step that already exists in the pipeline — check the item's
  artifact set first, because duplicating an existing gate is noise.

### 5. Write the critique report

Emit one structured report to the item root; mutate nothing else.

**Constraints:**
- You MUST write the report to `<item-root>/content-critique.md`, because the item root is
  where all sibling gate reports live.
- You MUST NOT modify any artifact other than your own report, because you are an outside
  reviewer, not an editor.
- You MUST use the output format below.

## Output format (`content-critique.md`)

```markdown
# Content Critique — <slug>

**Reviewer:** content-critique (<model>, independent) · **Date:** <YYYY-MM-DD>
**Item:** <item-root>
**Scope:** both | outcome | process
**Verdict:** SHIP | FIX-THEN-SHIP | REWORK — <one line why>

## Artifacts reviewed (depth honesty)
- <artifact> — read in full | skimmed | absent | not accessible (why)

## Outcome findings
> Severity: Blocker (must fix before publish) / Major / Minor / Nit

### Per-artifact
- [SEVERITY] <artifact:pointer> — <exact problem> → <precise fix>

### Cross-artifact
- [SEVERITY] <problem: FAQ vs post / thesis drift / image vs argument> → <fix>

## Process findings & proposals
### Weaknesses (evidenced)
- [SEVERITY] <pipeline gap, tied to an observed finding> → <fix>
### Improvement proposals (incl. out-of-box)
- [PROPOSAL] <extra step / methodology / different model / tooling> — would catch/improve: <finding>

## Prioritized recommendation list
1. <highest-value action> …
```

## Invocation

- **Interactive:** trigger this skill on the pipeline agent with the item id.
- **Headless / cross-model (recommended for independence):**
  `kiro-cli chat --no-interactive --model <a-model-different-from-the-drafter> --agent .kiro/agents/content-pipeline.json "critique content item <date>-<slug> (scope: both)"`
  — the agent is MCP-free, so nested/headless invocation does not hit MCP-initialization hangs.

## Notes

- File + web + image tools only by design. Do not add MCP servers — nested MCP loading blocks
  headless invocation.
- This skill is a *supplement*, not a replacement, for the critic agent (technical-rigor gate)
  and the `post-creation` per-step gates.

## Phasing (avoid response timeouts)

A critique touches many artifacts plus external fetches; doing it in one or two turns reliably
blows the response budget. Run it in four phases, one per turn:

| Phase | Turn | Work |
|---|---|---|
| 1 | turn 1 | Enumerate and read ALL local **text** artifacts in one parallel batch |
| 2 | turn 2 | Read **images** (downscaled ≤1400px, ≤4 per batch) and fetch external claim sources (≤3 URLs per turn) |
| 3 | turn 3 | Run cross-artifact consistency checks and compute findings |
| 4 | turn 4 | Write `content-critique.md` |

Never merge phase 4 into phase 3 — the report write is the deliverable and must not share a
turn with analysis. When fetching live pages for HTML analysis, request with
`Accept-Encoding: identity` (or a decompression-aware fetch) on the FIRST attempt.
