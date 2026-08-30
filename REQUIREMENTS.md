# Requirements

Everything the pipeline needs, whether it's required or optional, and how to satisfy it. The **core ideation → final draft flow needs only the "Required" rows** — no MCP servers, no cloud accounts.

## Required

| Dependency | Why | How to satisfy |
|------------|-----|----------------|
| **Kiro CLI** | Reference agent runtime that loads the skills | Install from https://kiro.dev, then `kiro-cli login` |
| **Python 3** | Runs the quality-scanner scripts | Preinstalled on macOS/Linux; scripts are stdlib-only (no `pip install`) |
| **Built-in tools** | `read, write, glob, grep, shell, web_fetch, web_search` | Provided by Kiro CLI out of the box — declared in `.kiro/agents/content-pipeline.json` |

## Optional (feature-flagged; off by default)

| Dependency | Enables | If absent |
|------------|---------|-----------|
| **yt-dlp** | Seeding ideation from a YouTube URL (transcript extraction) | Use non-YouTube triggers; or `brew install yt-dlp` / `pip install yt-dlp` |
| **An image-generation tool** | Actually rendering images (the pipeline always produces image *prompts*; generation is BYO) | You get prompt text to paste into your own image tool |
| **`style_corpus_dir` (your prior posts)** | Authentic voice/format matching in drafting | Ships with synthesized example posts; drafts still work, voice is generic until you point at your own corpus |
| **`site_public_base_url` / `prior_work_dir`** | Referencing your own earlier work | Those reference-gathering steps are skipped |
| **A second LLM (different model)** | The independent-model critique (humanize-pipeline stage 4, `content-critique`) — invoke `.kiro/agents/critic.json` with `--model <other-model>` | The gate is marked NOT SATISFIED (fail-loud); never silently replaced by a same-model review |

## Inputs you provide (via config)

See [CONFIGURATION.md](CONFIGURATION.md). In short, to use the pipeline on **your own** content rather than the examples, fill in:

- `content-paths.local.json` → `workspace_root` (your workspace) and `content_root` (where drafts go).
- `pipeline.local.json` → `style_corpus_dir` (your prior posts), and optionally `image_guidelines_path`, `user_aliases`, `site_public_base_url`, `prior_work_dir`.

## What is deliberately NOT required

- **No auto-sa.** This repo is fully standalone.
- **No MCP servers** (Slack, email, SFDC, internal image tools) on the critical path.
- **No AWS account, no cloud services** for the ideation → draft flow.
- **No blog/CMS.** Publishing is out of scope; the pipeline ends at a review-ready markdown draft.
