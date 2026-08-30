# kiro-content-pipeline

Take a content idea from **ideation → final draft** — with the quality and fact-check gates that keep published writing honest and in your own voice. Runs as a self-contained [Kiro CLI](https://kiro.dev) agent; the underlying quality scanners are plain Python CLIs you can run anywhere.

## What it does

Five skills form the pipeline:

1. **`ideation-session`** (interactive) — turn a trigger (an idea, a doc, a URL) into a finalized `ideation.md`: thesis, in/out of scope, resource map, seeded claim ledger. This is the Definition-of-Ready that locks *what* you're writing before drafting.
2. **`post-creation`** — draft the post in Obsidian-flavored markdown, then run the quality gates: challenge questions, reader FAQ, AI-smell scan, claim & citation verification, visual QA, and image prompts. Output is a polished `post.md` plus its companion quality docs.
3. **`humanize-pipeline`** — the layered humanization gate behind post-creation Step 11: deterministic AI-smell pre-pass → voice-calibrated LLM rewrite (against YOUR `voice/VOICE.md` profile) → deterministic re-scan gate → independent-model critique on a *different* model → advisory detector telemetry.
4. **`content-critique`** — independent outside review of the whole content item (post + FAQ + gate reports + images) on a different model: challenges the gate reports, checks cross-artifact consistency, and critiques the process itself.
5. **`fact-check`** — standalone pre-publication claim verification and internal-leak scan for any public-facing artifact.

**Out of scope by design:** publishing to a blog/CMS, deploy, and social scheduling. The pipeline stops at a review-ready final draft in markdown. You publish it however you like.

## Runs in Kiro — but not locked to Kiro

- **Scanner scripts** (`scripts/*.py`: AI-smell, citation verification, leak scan, visual QA, path resolver) are **stdlib-only Python CLIs** — run them anywhere with Python 3, no agent required.
- **Skill workflows** (`.kiro/skills/**/SKILL.md`) are structured prompt-workflows that call only generic tools (read/write/glob/grep/shell/web_fetch/web_search). Kiro CLI is the reference runtime; any capable agent could follow them.

## Quick start

```bash
# 1. Install Kiro CLI  →  https://kiro.dev
# 2. Clone this repo
git clone <repo-url> && cd kiro-content-pipeline

# 3. (Optional) point config at your own workspace — defaults use the bundled examples/
cp config/content-paths.sample.json config/content-paths.local.json
cp config/pipeline.sample.json      config/pipeline.local.json
#   edit the .local.json files (see CONFIGURATION.md)

# 4. Run the bundled agent
kiro-cli chat --agent .kiro/agents/content-pipeline.json
> ideate on <your idea>
```

With no config edits, it runs against the synthesized `examples/` workspace so you can see the full flow before pointing it at your own content.

## Requirements

- **Kiro CLI** (installed + logged in) — the reference runtime.
- **Python 3** — for the scanner scripts (stdlib only, no `pip install`).
- **yt-dlp** — *optional*, only if you seed ideation from a YouTube URL.
- **No MCP servers required** for the core pipeline. Image *generation* and any internal data sources are optional and off by default.

See **[REQUIREMENTS.md](REQUIREMENTS.md)** for the full dependency table and **[CONFIGURATION.md](CONFIGURATION.md)** for every config key.

## Repository layout

```
kiro-content-pipeline/
├── README.md · LICENSE · NOTICE · CONFIGURATION.md · REQUIREMENTS.md
├── config/            content-paths.sample.json · pipeline.sample.json
├── scripts/           content_paths.py + stdlib quality scanners
├── examples/          synthesized sample workspace (fresh clone runs E2E)
├── docs/              BACKFILL-REGISTER.md
└── .kiro/
    ├── agents/        content-pipeline.json · critic.json  (standalone; built-in tools only)
    ├── steering/      generic writing/ground-truth/pre-publish guardrails
    └── skills/        ideation-session · post-creation · humanize-pipeline · content-critique · fact-check
```

## License

Apache-2.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE).
