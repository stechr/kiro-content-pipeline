# Voice profile (for stage 2 voice calibration) — TEMPLATE

> [!important] Fill this in before your first real run
> This file is YOUR standing voice sample. Stage 2 of the humanize pipeline loads it on
> every run and calibrates the rewrite to it. Per the blader/humanizer Voice Calibration
> rule, this sample OVERRIDES the humanizer's own style rules where they conflict — the
> whole point is that the rewrite sounds like *you*, not like "default de-AI'd text".
>
> Until you replace it, this template describes the **fictional example author** whose
> posts ship in `examples/vault/style-corpus/` — so a fresh clone runs end-to-end.
> The pipeline resolves this file via the `voice_profile_path` key in
> `config/pipeline.local.json` (default: this file).

## Primary corpus — your published writing

List 2–5 pieces of YOUR public writing (URLs or file paths). Public content only — no
private drafts, no PII beyond what is already published.

- `${REPO}/examples/vault/style-corpus/2026-05-10-clever-code.md` (example author)
- `${REPO}/examples/vault/style-corpus/2026-05-24-ship-checklist.md` (example author)
- `${REPO}/examples/vault/style-corpus/2026-06-07-code-review-week.md` (example author)

## Extracted voice traits

Read your corpus and write down the 5–8 concrete, observable habits that make your prose
yours. Be specific — "conversational" is useless; "opens sections with a direct question"
is calibratable. The example-author traits below show the expected granularity:

1. Short declarative openers; the first sentence of a section states the point outright.
2. First-person experience anchors ("I tried this on a real review", "took me an afternoon").
3. Occasional direct reader address mid-argument ("You've seen this one.").
4. Plain verbs over formal ones ("use" not "utilize", "is" not "serves as").
5. Em dashes at a low natural rate — a few per 1,000 words, never more than the
   scanner's hard limit (18/1k).
6. Bold reserved for pseudo-headings ("**Repo:**"), not mid-sentence emphasis.
7. Headings in sentence case.

> When a trait of yours conflicts with a humanizer rule (e.g. you legitimately use em
> dashes, or you DO use "Title Case" headings), note the override here explicitly —
> stage 2 honors this file over the generic rules, and the deterministic scanner tiers
> such items as STYLE (informational), not failures.

## Gold-standard examples

Optionally point at 1–3 posts that show the *target end state* — pieces you wrote or
hand-edited that you consider fully "you". The style corpus above doubles as this for
the example author.

## Known failure mode (keep this section)

Adding voice can re-introduce soft AI vocabulary ("remarkable"-class words) — that is
exactly what stage 3 (the deterministic post-pass) exists to catch. Do not remove the
stage-3 gate because stage 2 "already knows the rules".
