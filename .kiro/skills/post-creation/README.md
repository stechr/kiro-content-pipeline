# post-creation

Turn a source (a note, an article URL, or a topic idea) into a polished, review-ready draft — with quality and fact-check gates — in Obsidian-flavored markdown.

## Why it exists

Drafting is only half the job; a publishable post also needs voice-matching, challenge questions, a reader FAQ, an AI-smell pass, claim/leak verification, and visual QA. This skill runs all of that as one pipeline and leaves every gate's report on disk, so the final draft is genuinely review-ready. Output is platform-agnostic — publish it wherever you like (publishing itself is out of scope).

## How to use it

- "write a post about [[note-name]]"
- "draft an article about <topic>"
- "create a post about https://example.com/article focusing on <angle>"

If a finalized `ideation.md` exists for the item (from `ideation-session`), Step 0 ingests it as the binding spec. Otherwise the skill works straight from the source you give it.

## Scope

Steps 0–11e (draft + quality gates) plus Step 12 (image *prompts*). Image generation, social teasers, and publishing are downstream/out of scope. Paths and user-specific inputs (style corpus, image guidelines, aliases) resolve through `scripts/content_paths.py` — see the repo's `CONFIGURATION.md`.
