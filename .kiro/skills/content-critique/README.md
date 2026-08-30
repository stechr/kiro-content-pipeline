# content-critique

Independent outside review of a **whole content item** — the post plus every companion
artifact (FAQ, challenging questions, gate reports, images, ideation) — on a model
**different** from the one that drafted it.

## What it adds over the built-in gates

The `post-creation` gates are per-artifact and run inside the drafting session. This skill:

- re-derives quality/correctness findings **skeptically** instead of trusting the gate reports,
- checks **cross-artifact consistency** (thesis drift between ideation and post, FAQ vs post,
  images vs argument) that no per-artifact gate can see,
- critiques the **process** (missing artifacts, gates that missed defects, ordering) and makes
  labeled improvement **proposals**.

## Run

```bash
# headless, on a model different from your drafting model:
kiro-cli chat --no-interactive --model <other-model> \
  --agent .kiro/agents/content-pipeline.json \
  "critique content item 2026-07-02-own-your-real-estate (scope: both)"
```

Output: `<item-root>/content-critique.md` with a SHIP / FIX-THEN-SHIP / REWORK verdict,
severity-tagged findings, and a prioritized recommendation list. The reviewer never edits
any artifact except its own report.

## Independence rules

- Different model than the drafter — same-model self-review demonstrably misses issues the
  drafting model is blind to.
- Gate reports are treated as claims to challenge, not evidence.
- Every "Verified" verdict must quote the fetched source verbatim.
- Depth honesty: the report states what was read in full vs skimmed vs inaccessible.
