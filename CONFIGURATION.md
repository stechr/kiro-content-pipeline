# Configuration

The pipeline never hardcodes paths or user-specific values. Everything resolves through two JSON files, read by `scripts/content_paths.py`:

| File | Purpose | Tracked? |
|------|---------|----------|
| `config/content-paths.sample.json` | Schema + example for **path** config | ✅ tracked |
| `config/content-paths.local.json` | **Your** paths (copy of the sample) | ❌ gitignored |
| `config/pipeline.sample.json` | Schema + example for **non-path** values | ✅ tracked |
| `config/pipeline.local.json` | **Your** non-path values (copy of the sample) | ❌ gitignored |
| `config/leak-patterns.sample.json` | Generic **org-internal leak patterns** for `leak_scan.py` (example format) | ✅ tracked |
| `config/leak-patterns.local.json` | **Your organization's** internal markers (copy of the sample) | ❌ gitignored |

If a `.local.json` is absent, the resolver falls back to the `.sample.json`, whose defaults point at the bundled `examples/` workspace — so a fresh clone runs with **zero configuration**.

Token expansion in values: `${HOME}`, `${workspace_root}`, `${content_root}`.

## content-paths keys

| Key | Meaning | Default |
|-----|---------|---------|
| `workspace_root` | Root of your content workspace (e.g. an Obsidian vault, or any folder tree) | `examples/vault` |
| `content_root` | Where per-item draft folders are written | `${workspace_root}/drafts` |
| `item_subfolders` | Channel subfolder names within an item folder | `{ blog, linkedin }` |
| `item_files.manifest` | Cross-channel manifest filename | `content-item.md` |

**Item folder layout** (created by the pipeline):

```
content_root/<date>-<slug>/
├── content-item.md          cross-channel manifest
├── ideation.md              the finalized Definition-of-Ready
├── faq.md · challenging-questions.md · ai-smell.md · claim-verification.md · visual-qa.md
├── assets/                  images / diagrams
├── blog/      post.md       the draft
└── linkedin/  (optional teaser artifacts)
```

## pipeline keys

| Key | Meaning | Step | Default / if empty |
|-----|---------|------|--------------------|
| `style_corpus_dir` | Folder of **your prior posts** for voice/format matching | post-creation §5 | bundled example posts |
| `prior_work_dir` | Local folder to search for your own earlier work to reference | post-creation §3 | `""` → step skipped |
| `site_public_base_url` | Public base URL of your published work (own-work references) | post-creation §3 | `""` → website search skipped |
| `user_aliases` | Your internal login/alias(es) — the leak gate flags accidental leaks | post-creation §11d (leak scan) | `[]` |
| `image_guidelines_path` | Markdown file of **your** image-prompt guidelines | post-creation §12 | generic example guidelines |
| `voice_profile_path` | **Your** voice profile (corpus + extracted traits) for the humanize rewrite | humanize-pipeline stage 2 | bundled template (fictional example author) |

Keys left empty make their step **optional** (skipped, not an error) — nothing blocks the core ideation → draft flow.

## Leak-scan patterns (`leak_scan.py`)

The internal-leak gate (post-creation §11d) applies two pattern sets:

- **Built-in, org-neutral** (always on, no config needed): personal filesystem paths (`/Users/…`, `/home/…`) and 12-digit cloud account IDs.
- **Org-specific** (yours): your organization's internal markers — internal email domains, chat/wiki/tool links, internal hostnames, codenames. Copy `config/leak-patterns.sample.json` → `config/leak-patterns.local.json` (gitignored) and replace the examples with your own. Each entry is `{ label, regex, note }`; a match blocks publish.

Resolution order: `--patterns FILE` → `$LEAK_PATTERNS_CONFIG` → `config/leak-patterns.local.json` → `config/leak-patterns.sample.json`. Aliases to flag come from `pipeline.local.json` → `user_aliases` (passed via `--aliases`).

## Resolving a path at runtime

```bash
python3 scripts/content_paths.py get content_root
python3 scripts/content_paths.py item-dir 2026-07-02-my-post
python3 scripts/content_paths.py channel-dir 2026-07-02-my-post blog
python3 scripts/content_paths.py dump
```
