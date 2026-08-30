# humanize-pipeline

Removes AI-writing tells from a drafted post while keeping the author's voice, facts,
and structure intact. This is the canonical quality gate behind post-creation Step 11.

## Why layered

A single "humanize this" LLM pass is unreliable in both directions: it misses mechanical
tells and it scrubs legitimate authorial voice. The pipeline splits the job:

| Stage | What | Tool |
|---|---|---|
| 1 | Deterministic pre-pass → concrete fix list | `scripts/humanize_check.py pre` (wraps the repo's `ai_smell_scan.py`) |
| 2 | Voice-calibrated LLM rewrite | humanizer methodology + YOUR `voice/VOICE.md` profile |
| 3 | Deterministic re-scan — exit criterion: zero must-fix | `scripts/humanize_check.py post` |
| 4 | Independent-model critique (substance, not style) | `.kiro/agents/critic.json` on a DIFFERENT model |
| 5 | Detector score | advisory telemetry only — never edit to move a score |

Stage 3 exists because stage 2 provably re-introduces mechanical tells; stage 4 runs on
a different model because same-model self-review misses what the drafting model is
blind to.

## Setup

1. Fill in `voice/VOICE.md` with your public writing corpus and extracted voice traits
   (ships pre-filled for the bundled fictional example author, so a fresh clone runs).
2. Optionally set `voice_profile_path` in `config/pipeline.local.json` to point at a
   copy elsewhere.
3. For stage 4, pick a model different from your drafting model and pass it via
   `--model` when invoking the critic agent.

## Run

```bash
python3 .kiro/skills/humanize-pipeline/scripts/humanize_check.py pre  drafts/my-post/post.md
# ... stage-2 rewrite with the fix list + voice profile ...
python3 .kiro/skills/humanize-pipeline/scripts/humanize_check.py post drafts/my-post/post.md
python3 .kiro/skills/humanize-pipeline/scripts/humanize_check.py --self-test
```

Hard rules: no fabrication, verbatim quotes are never reworded, frontmatter/code/links/
tables stay byte-identical, and the stage-4 gate is never silently downgraded to a
same-model review.
