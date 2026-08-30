---
name: ideation-session
description: "Interactive, human-in-the-loop ideation session that turns a trigger (a user idea, a note, an RSS/reading-list entry, any prior artifact) into a finalized ideation draft — the Definition-of-Ready for the content pipeline. Locks WHAT we're writing (thesis, in/out of scope, resource map, claim ledger, derivatives) BEFORE drafting. Use when the user says 'ideate', 'ideation session', 'let's ideate on', 'lock the angle', 'prep an ideation draft', 'scope a post', 'what should this post say', or wants to nail down a post's thesis and sources before drafting."
requires:
  steering: [writing-guardrails.md, ground-truth.md]
---

# Ideation Session

## Overview

An **interactive, human-in-the-loop** session where the user and the model jointly turn a trigger into a solid **ideation draft** (`ideation.md`). The ideation draft is the **Definition-of-Ready (DoR)** for the content pipeline: it locks WHAT we are writing — thesis, audience, in-scope, out-of-scope, the resource map, a seeded claim ledger, and the derivative plan — BEFORE drafting starts.

This exists because grooming the *container* (topic, voice, scope) is not enough. Drafting with no locked *content* invents an angle, and a wrong angle propagates into everything derived from the post — a whole review cycle spent unwinding it. This session is the fix: resolve the angle and the sources interactively, with the human in the loop, and only then authorize drafting.

## General Constraints

- **IDEAS ONLY — no prose.** You MUST capture everything as bullet points. You MUST NOT write full paragraphs or polished sentences, because polishing happens later in the post-creation pipeline; the focus here is transporting ideas/messages between user and model. Diagrams MUST be sketched in WORDS or ASCII art, not rendered.
- **Interactive, not autonomous.** You MUST treat this as a back-and-forth with the user. You MUST surface open questions, proposals, and trade-offs for the user to react to, rather than silently deciding the angle yourself.
- **No drafting until finalized.** You MUST NOT start, or instruct anyone to start, the drafting stage (`post-creation`) until the user has flipped the draft to `status: finalized`, because an un-finalized draft has not passed the DoR and the angle is not locked.
- **No content produced here.** You MUST NOT write `post.md`, a teaser, or any publishable artifact in this session. This session produces the ideation draft ONLY.
- **Apply the steering guardrails.** Before proposing the angle, you MUST read `steering/writing-guardrails.md` → "Framing of tools, vendors, and platforms you build on" and "Feature the code repo in every derivative", because both shape the locked thesis/derivatives (an unlocked angle is exactly what lets a negative-framing drift propagate into every derivative).

## Parameters

- **trigger** (required): The seed for the session. FLEXIBLE — MAY be a free-text user idea, a note path/wikilink, an RSS or reading-list entry, or any prior artifact (a published post to follow up on, a research note, a chat thread).
- **slug** (optional): Proposed kebab-case blog slug. If absent, propose one from the thesis and confirm with the user.
- **target_date** (optional): Intended publish date (YYYY-MM-DD). If absent, leave as a placeholder for the user to fill.

## Workflow

### 1. Absorb the Trigger

Understand the seed and what the user wants out of it.

**Constraints:**
- You MUST identify the trigger type (user idea / note / RSS / reading-list / prior artifact) and read or fetch its full content before proposing anything, because a thesis built on a snippet drifts.
- If the trigger is a note or local file, you MUST read it in full. If it is a URL, you MUST fetch it (`web_fetch`; `yt-dlp` for YouTube per `ground-truth.md`).
- If the trigger references a primary source the post would build on, you MUST fetch that source's full content and assess overlap, because a post that re-tells its source is derivative — flag that risk now, not mid-draft.
- You MUST present a short bullet read-back of what you understood the trigger to be, and ask the user to confirm or correct, before proposing a thesis.

### 2. Propose and Lock the Thesis

Converge on the single core message.

**Constraints:**
- You MUST propose 1-3 candidate one-line theses as bullets and ask the user to pick or refine one, because the thesis is the spine everything else hangs off.
- You MUST keep the thesis to ONE line — if it needs two sentences, it is two posts or an unfocused angle; say so.
- You MUST capture the audience and reader intent as bullets (who · what they do after reading).
- When proposing the angle, you MUST NOT frame the tools/platform you build on negatively and MUST NOT add defensive hedging where a managed service already handles the concern appropriately (per `steering/writing-guardrails.md` → "Framing of tools, vendors, and platforms you build on") — surface a positive/neutral framing instead.
- You MUST NOT proceed to scope until the user has confirmed a single thesis.

### 3. Draw the Scope Boundaries

Lock what is in and — critically — what is out.

**Constraints:**
- You MUST capture **In scope** as bullets (the moves the post WILL make).
- You MUST capture **Out of scope** as bullets framed as explicit "do NOT cover" guardrails, because out-of-scope is what stops the drafting stage from wandering into the wrong angle. An ideation draft with an empty out-of-scope list is incomplete.
- You SHOULD propose out-of-scope items the user might not think of (tangents the source invites, competitor comparisons, negative-framing angles) and ask the user to confirm them as guardrails.

### 4. Build the Resource Map (with time-boxed joint research)

Assemble the sources and resolve open questions.

**Constraints:**
- You MUST list **Internal** resources (local notes, and — optional — internal chat/docs/knowledge sources) and mark ground-truth ones with ★, each with a one-line "why".
- You MUST list **External** resources (URLs) and note which claim each supports.
- You MUST capture **Open questions** as bullets, then do **time-boxed joint research** (~20 minutes / ~5 sources) to resolve them into findings and to find supporting/contrasting external sources. You MUST NOT exceed ~5 fetched sources in this phase, because diminishing returns — surface what is still open rather than over-researching.
- For each open question you MUST record `question -> finding` as a bullet (or `-> unresolved` if research did not settle it).
- You MUST honour the trust hierarchy in `ground-truth.md`: product/feature claims need an official-doc source; chat/notes are lower-tier and MUST be flagged as such in the resource map.
- The DoR requires **≥2 internal AND ≥2 external** resources in the map. If the map falls short after research, you MUST tell the user it is not yet ready to finalize and what is missing.

### 5. Seed the Claim Ledger

Pre-list the load-bearing claims so the downstream fact-check/leak gate has a head start.

**Constraints:**
- You MUST seed a claim ledger as bullets: `claim | source | type` where type ∈ {external / first-party / opinion}.
- You MUST classify any claim knowable only from internal sources as a **leak risk** and note it must be re-grounded to a public source, softened to "in my testing", or dropped — do NOT carry it forward as universal fact.
- You SHOULD flag legal-implication claims (data retention, residency, who-can-access, pricing, security guarantees) for extra scrutiny in the downstream gate.
- The ledger is a SEED, not the final audit — the post-creation Step 11d gate verifies it. The DoR only requires the ledger be seeded (non-empty).

### 6. Decide the Derivatives

Lock the visual/derivative plan, including the repo decision.

**Constraints:**
- You MUST capture, as bullets: a **hero concept** (in words) and **diagram sketches** (ASCII/word only). You MAY also capture a **teaser hook** and **video scene priorities** if you plan to produce those derivatives downstream (optional — this pipeline ends at the final draft + image prompts).
- You MUST record **repo featured?** as `<repo-url | no>`. If a repo is featured, you MUST note that — per `steering/writing-guardrails.md` → "Feature the code repo in every derivative" — every derivative that gets produced MUST feature the repo (name it and link it). This decision is part of the DoR. (Note: this pipeline ends at the final draft + image prompts; teaser/video derivatives are OPTIONAL downstream stages — capture their plan if you produce them, otherwise leave as `n/a`.)
- You MUST capture a **Risks / flags** list: competitor mentions, sensitive/legal claims, first-person anecdotes to verify, and any negative-framing risk — so drafting and review know what to watch.

### 7. Write the Ideation Draft

Persist the draft to the content-item folder.

**Constraints:**
- You MUST read `references/ideation-template.md` and follow its schema EXACTLY — it is the locked spec; do not redesign it.
- You MUST resolve the item folder via the path config, never hardcode it:
  ```bash
  python3 scripts/content_paths.py item-dir <date>-<slug>
  ```
  Create the folder if it does not exist. The ideation draft is a **shared, cross-channel artifact** (like `faq.md`) and MUST sit at the **item root**: `<date>-<slug>/ideation.md` — NOT inside a channel subfolder.
- You MUST write the draft with `status: draft`, because the user — not the model — authorizes finalization.
- You MUST keep every section as bullets / ASCII per the IDEAS-ONLY constraint.
- After writing, you MUST present the Definition-of-Ready checklist (Step 8) and tell the user the draft is saved at the resolved path.

### 8. Definition-of-Ready Gate and Finalization

The user confirms finalization; the model never self-finalizes.

**Constraints:**
- You MUST present the **Definition-of-Ready checklist** and mark each item ✓ or ✗ against the draft:
  - [ ] Thesis — one line, confirmed by the user
  - [ ] In scope — at least one bullet
  - [ ] Out of scope — at least one explicit "do NOT cover" guardrail
  - [ ] Resource map — ≥2 internal AND ≥2 external sources
  - [ ] Claim ledger — seeded (non-empty)
  - [ ] Derivatives decided — hero/diagram sketches + **repo featured? answered** (`<repo-url | no>`); teaser/video priorities optional (downstream stages)
- You MUST NOT change `status` to `finalized` yourself. You MUST ask the user to confirm finalization; ONLY when the user explicitly confirms do you flip `status: draft` → `status: finalized` in the frontmatter.
- If any DoR item is ✗, you MUST tell the user it is not ready and what is missing, and you MUST NOT finalize, because finalization is the authorization signal for the content pipeline.
- After finalization you MAY remind the user of the next step (run `post-creation`, which reads this finalized ideation draft as its binding input), but the user decides when to start it.

## End-to-End Flow

This skill is the FIRST stage of the content pipeline:

```
ideation-session (interactive)
   └─ ideation.md  status: draft ──(user confirms DoR)──> status: finalized
        │
        ▼
post-creation
   ├─ Step 0 ingests the finalized ideation.md as binding input
   │    thesis = post spine · out-of-scope = hard guardrails
   │    claim ledger seeds the fact-check/leak gate · derivatives inform image prompts
   ├─ Steps 1-11e  (local draft + all quality gates: challenge Qs, FAQ,
   │                AI-smell, claim/leak verification, visual QA)
   └─ Step 12      (image prompts)
        │
        ▼
final draft (review-ready markdown)  ──▶  fact-check (optional standalone pass)
```

Publishing to a blog/CMS is out of scope — the pipeline ends at a review-ready final draft. See the `post-creation` skill for the consuming side.

## Examples

### From a user idea

```
User: "ideate on a post about agentic eval harnesses"
Agent: [reads writing-guardrails]
       [reads any referenced source in full, presents a bullet read-back]
       [proposes 3 one-line theses → user picks one]
       [locks in/out of scope as bullets]
       [builds resource map; does ~20 min / ~5 source joint research on open questions]
       [seeds claim ledger; decides derivatives incl. repo featured? = <url|no>]
       [resolves item-dir via content_paths.py, writes ideation.md status: draft]
       [presents DoR checklist; user confirms → flips to status: finalized]
```

### From a note or an RSS / reading-list item

```
User: "ideate on the RSS item about <feature>"
Agent: [reads the item + the linked source in full]
       [same flow → ideation.md at <date>-<slug>/ideation.md, status: draft]
       [DoR gate → user finalizes → ready to run post-creation]
```
