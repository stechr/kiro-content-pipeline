# Ideation Draft Template (`ideation.md`)

This is the **locked schema** for the ideation draft. Implement it EXACTLY — do not redesign,
reorder, or rename sections. The draft is the Definition-of-Ready (DoR) for the content pipeline.

- Location: the **item root** of the content-item folder — `<date>-<slug>/ideation.md` — a
  shared, cross-channel artifact (like `faq.md`), NOT inside a channel subfolder.
- Resolve the folder via `python3 scripts/content_paths.py item-dir <date>-<slug>`.
- IDEAS ONLY: every section is **bullets**, no prose paragraphs. Diagrams are ASCII / word sketches.
- `status` starts as `draft`. The **user** flips it to `finalized` to authorize the drafting stage
  (`post-creation`) — the model never self-finalizes.

## Schema (copy this exactly)

```markdown
---
type: ideation-draft
status: draft            # user flips to "finalized" to authorize handoff
title_candidates: [ ... ]
slug: <proposed>
target_date: <YYYY-MM-DD>
---

## Thesis (one line)
- <the single core message; everything hangs off this>

## Audience & intent
- who: <reader>
- what they do after reading: <action>

## In scope (bullets)
- <will cover ...>

## Out of scope (bullets)
- do NOT cover <...>     # explicit guardrails — stops a bg run wandering into the wrong angle

## Resource map
- Internal (★ = ground-truth):
  - ★ <path / url / internal source> — why
  - <path / url / internal source> — why
- External:
  - <url> — supports which claim
  - <url> — supports which claim
- Open questions -> research now:
  - <question> -> <finding>        # or "-> unresolved"

## Claim ledger (seed)
- <claim> | <source> | external
- <claim> | <source> | first-party
- <claim> | <source> | opinion

## Derivatives
- hero concept (words): <...>
- diagrams (ascii/word sketch):
  - <sketch>
- repo featured?: <repo-url | no>   # if a url -> every derivative produced MUST feature it (writing-guardrails)
- teaser hook: <bullet | n/a>              # optional — only if you produce a teaser downstream
- video scene priorities: <n/a>            # optional — only if you produce a video downstream

## Risks / flags
- competitor mentions: <...>
- sensitive/legal claims: <...>
- first-person anecdotes to verify: <...>
- negative-framing risk: <...>
```

## Definition-of-Ready checklist (must pass before finalization)

The draft is ready to finalize only when ALL of these are ✓:

- [ ] **Thesis** — one line, confirmed by the user
- [ ] **In scope** — at least one bullet
- [ ] **Out of scope** — at least one explicit "do NOT cover" guardrail
- [ ] **Resource map** — **≥2 internal AND ≥2 external** sources
- [ ] **Claim ledger** — seeded (non-empty)
- [ ] **Derivatives decided** — hero/diagram sketches + **repo featured? answered** (`<repo-url | no>`) + **diagram renderer chosen** (declarative-diagram tool default · hand-authored `svg` for charts · other renderers only with a written justification); teaser/video priorities optional (downstream stages)

If any item is ✗, the draft stays `status: draft` and the model tells the user what is missing.

## Notes on specific fields

- **Thesis** is the post's spine: post-creation Step 0 treats it as binding and builds the post
  around it. Keep it to ONE line — two sentences means two posts or an unfocused angle.
- **Out of scope** becomes **hard guardrails** for the downstream run. An empty out-of-scope list
  is the failure mode that let a wrong negative-framing angle propagate through every derivative.
- **Claim ledger** is a SEED only — it gives the post-creation fact-check/leak gate (Step 11d) a
  head start. Anything knowable only from internal sources is a **leak risk**: re-ground to a
  public source, soften to "in my testing", or drop it. Flag legal-implication claims for extra
  scrutiny.
- **repo featured?** — if a repo URL is given, every derivative that gets produced MUST feature
  it (see `steering/writing-guardrails.md` → "Feature the code repo in every derivative"). This is
  part of the DoR, not an afterthought. (Teaser/video are optional downstream stages in this
  pipeline; if you produce them, they feature the repo too.)
- **negative-framing risk** — per `steering/writing-guardrails.md` → "Framing of tools, vendors,
  and platforms you build on", the thesis/angle must not frame the platform/tools you build on as
  a liability or add defensive hedging. Flag it here so drafting and review watch for it.
