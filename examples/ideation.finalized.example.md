---
type: ideation-draft
status: finalized
title_candidates: ["Version Your Prompts Like Code", "Prompts Are Source Too", "Stop Losing Your Best Prompts"]
slug: version-your-prompts
target_date: 2026-07-15
---

<!--
WORKED EXAMPLE — a finalized ideation.md (the Definition-of-Ready).
In a real run this file lives at the item root: content_root/<date>-<slug>/ideation.md
(resolve with: python3 scripts/content_paths.py item-dir <date>-<slug>).
It is kept here in examples/ purely as a reference of a completed draft.
-->

## Thesis (one line)
- Treat prompts as source code — version them, review them, test them — because an un-versioned prompt is a result you can't reproduce.

## Audience & intent
- who: developers and technical writers using LLMs in a real workflow
- what they do after reading: put their prompts under version control and add a tiny regression check

## In scope (bullets)
- why an ad-hoc prompt is a reproducibility problem
- a minimal pattern: prompts in files, in git, with a one-line diff on change
- a cheap "does it still work" check (a fixed input → expected-shape output)

## Out of scope (bullets)
- do NOT cover model-provider comparisons or benchmarks
- do NOT cover prompt-injection security (separate topic)
- do NOT frame any specific tool/provider negatively

## Resource map
- Internal (★ = ground-truth):
  - ★ examples/vault/style-corpus/2026-05-24-ship-checklist.md — the checklist voice/format to echo
  - examples/vault/style-corpus/2026-05-10-clever-code.md — the "boring wins" throughline
- External:
  - https://martinfowler.com/articles/2011-refactoring-tools.html — supports the "treat text as an artifact you refactor" angle
  - https://google.github.io/eng-practices/review/reviewer/ — supports the "review the diff, ask questions" angle
- Open questions -> research now:
  - is there a widely-cited definition of "prompt regression testing"? -> unresolved; frame as first-party practice, not a cited standard

## Claim ledger (seed)
- an un-versioned prompt cannot be reproduced reliably | first-party (my experience) | first-party
- diffing a prompt change surfaces intent, like a code diff | martinfowler.com | external
- reviewing prompts with questions beats prescribing edits | google eng-practices | external

## Derivatives
- hero concept (words): a plain text file open next to a terminal, warm light, a git diff visible — "prompt as source"
- diagrams (ascii/word sketch):
  - flow: edit prompt -> git diff -> run fixed-input check -> commit
- repo featured?: no
- teaser hook: n/a
- video scene priorities: n/a

## Risks / flags
- competitor mentions: none — keep providers generic
- sensitive/legal claims: none
- first-person anecdotes to verify: the "I lost my best prompt" opener must be true or hedged
- negative-framing risk: do not frame LLM providers as unreliable; the point is *our* process, not their fault
