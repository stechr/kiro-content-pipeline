# Examples — synthesized workspace

A self-contained, **synthesized** workspace so a fresh clone runs ideation → final draft with zero configuration. All content here is fictional (fictional author, fictional company names) — no real data.

```
examples/
├── ideation.finalized.example.md   ← a worked, finalized ideation.md (Definition-of-Ready)
└── vault/
    ├── drafts/          ← per-item draft folders are written here (output)
    ├── style-corpus/    ← 3 synthesized "prior posts" for voice/format matching (post-creation §5)
    └── guidelines/      ← generic image-prompt guidelines (post-creation §12)
```

The sample configs (`config/*.sample.json`) point here by default. Replace with your own workspace via `config/*.local.json` (see [CONFIGURATION.md](../CONFIGURATION.md)).

The three style-corpus posts share one fictional author voice (plain, direct, first-person, ends on a question) so Step 5 has a consistent signal to match. Swap in your own posts for authentic voice matching.
