# ideation-session

Interactive, human-in-the-loop session that turns a trigger into a finalized **ideation draft** (`ideation.md`) — the Definition-of-Ready for the content pipeline.

## Why it exists

Grooming the *container* (topic, voice, scope) is not enough. Drafting with no locked *content* lets the angle drift, and a wrong angle propagates into everything derived from the post — a whole review cycle spent unwinding it. The fix is an interactive phase that locks WHAT we're writing — thesis, in/out of scope, the resource map, a seeded claim ledger, and the derivative plan (incl. repo-featured?) — BEFORE drafting starts. The user, not the model, flips the draft from `draft` to `finalized`; only a finalized draft authorizes the drafting stage.

## How to use it

- "ideate on a post about agentic eval harnesses"
- "let's ideate on this RSS entry / note / reading-list item"
- "lock the angle before we start drafting"

Give it a trigger (an idea, a note, an RSS/reading-list item, or any prior artifact). It runs a back-and-forth — thesis → scope → resource map (with ~20 min / ~5 source joint research) → claim ledger → derivatives — writes `ideation.md` (status: `draft`) at the content-item root, then presents a Definition-of-Ready checklist. You finalize it; the content pipeline (`post-creation` Step 0) consumes it.

The exact `ideation.md` schema is in `references/ideation-template.md`.
