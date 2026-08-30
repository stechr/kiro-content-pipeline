---
name: post-creation
description: Create posts and articles from a source (a note, an external article URL, or a topic idea) — draft, run quality/fact-check gates, and generate image prompts. Use when user says "create post", "write a post", "draft a post", "post about", "write an article", or wants to turn source material into a review-ready draft.
requires:
  steering: [writing-guardrails.md, ground-truth.md, pre-publish-safety.md]
---

# Post Creation

## Overview

Turns any source material (a note, an external article URL, or a topic idea) into a polished, review-ready post or article in Obsidian-flavored markdown. Follows the author's established writing style (from the configured style corpus), runs quality and fact-check gates, and generates image prompts. Platform-agnostic — the output is a final draft you can publish anywhere. Publishing itself is out of scope.

## General Constraints

- **Suppress intermediate narration.** When executing the multi-step pipeline, do NOT surface turns like "Good, now let me..." or "Now I need to..." between steps. Only surface the final result or a genuine blocker.
- **Mermaid compatibility.** When generating Mermaid diagrams, default to well-supported types (flowchart, graph, sequenceDiagram, gantt). Newer types like `block-beta` may not render in all markdown viewers. If a newer type is used, add a proactive caveat and offer a fallback.
- **Draft path.** Always resolve the draft folder via `python3 scripts/content_paths.py` (never hardcode). Per-item drafts live under `content_root` — resolve with `content_paths.py item-dir <date>-<slug>`. Never save outside the configured workspace.
- **LinkedIn / social is a teaser, not a cross-post (guidance).** If you later produce a social teaser (a downstream stage, out of this pipeline's scope), the model is: the full article lives on your site, the teaser drives traffic — never "Cross-posted from…". This pipeline stops at the final draft; keep this note only as guidance for downstream derivatives.
- **Companion quality docs are MANDATORY, even in multi-post runs.** Step 9 (`challenging-questions.md`) and Step 10 (`faq.md`) are required pipeline artifacts, not optional extras. Any path that produces a publishable `post.md` MUST still run Steps 9 and 10 for EACH post and leave both docs at the item root (`content_paths.py item-dir <date>-<slug>`). Under budget/time pressure, write the post and its two companion docs before moving on — never a teaser-only draft.
- **Quality-gate artifacts are also MANDATORY and PERSISTED.** Beyond Steps 9-10, the quality gates MUST leave their reports on disk at the item root: `ai-smell.md` (Step 11), `claim-verification.md` (Step 11d), and `visual-qa.md` (Step 11e). Running a gate and discarding its output does NOT satisfy the step. These reports are what make a draft review-ready.
- **AWS implementation section (optional).** When the article covers architecture patterns relevant to a specific cloud/platform, you MAY add a practical "If You're Running This on <platform>" section near the end (after the vendor-neutral conclusion, before Sources) with concrete service mappings and doc links. Frame as practical implementation, not product promotion. Skip it for non-technical posts.

## Parameters

- **source_note** (optional): Path or wikilink to the note to base the post on
- **source_url** (optional): URL of an external article to respond to or build on
- **focus** (optional): Specific angle, topic, or section to emphasize
- **structure_hints** (optional): Rough outline, key points, or sections the user wants included
- **type** (optional, default: "post"): "post" for a long-form website/blog post (no char limit), "linkedin-post" for a short-form social post (≤3,000 chars), or "article" for long-form

At least one of `source_note` or `source_url` MUST be provided.

## Workflow

### 0. Ingest the Ideation Draft (if present)

If a finalized ideation draft exists for this content item, it is the **binding spec** for the post — it was produced by an interactive `ideation-session` (the Definition-of-Ready) and locks the angle BEFORE this run. If none exists, behave exactly as today and proceed to Step 1.

**Constraints:**
- You MUST check for an ideation draft at the content-item root: resolve the folder with `python3 scripts/content_paths.py item-dir <date>-<slug>` and look for `ideation.md`. If it does not exist, skip this step and proceed to Step 1 unchanged.
- If `ideation.md` exists but its frontmatter is `status: draft` (not `finalized`), you MUST treat it as NOT authorized: surface that the ideation draft is not finalized and either proceed without it (interactive runs) or — for a background run — note it and continue per the run's instructions. Do NOT treat a non-finalized draft as binding, because finalization is the user's authorization signal.
- When `status: finalized`, you MUST treat these sections as **binding inputs**, not suggestions:
  - **Thesis** → the post's spine; the draft MUST be built around this single message.
  - **In scope** → what the post covers.
  - **Out of scope** → **hard guardrails** — you MUST NOT cover these, because they exist specifically to stop the angle from drifting (the failure mode this whole stage fixes).
  - **Resource map** → the starting source set (Internal ★ = ground-truth, External, and resolved open-question findings). Use these as the primary references in Steps 2-4.
  - **Claim ledger (seed)** → seeds the fact-check/leak gate (Step 11d): carry these claims and their types into `claim-verification.md` and verify them there.
  - **Derivatives** → inform the image prompts (Step 12). If **repo featured?** is a URL, any derivative produced MUST feature the repo (per `steering/writing-guardrails.md` → "Feature the code repo in every derivative").
  - **Risks / flags** → carry into the relevant gates (competitor mentions, legal claims, first-person anecdotes to verify, negative-framing risk).
- **TBD preflight (hard-stop).** Before proceeding to Step 1, scan the finalized ideation's Resource map and Claim ledger for any `TBD`, `link TBD`, or `URL TBD` token. If any are found, STOP and surface them as a blocking input-gap — request resolution (or an explicit waiver) from the user first. Do NOT proceed with a fallback URL and "flag it later"; the finalized ideation is binding, so an unresolved reference can become a dangling link in the published post.
- You MUST honour the negative-framing guardrail from the ideation draft and `steering/writing-guardrails.md` — do not reintroduce a negative-framing or defensive angle the ideation phase ruled out.
- You MAY pull in resources beyond the ideation map when drafting requires it; note any such addition when you present the draft.

### 1. Read Source Material

Load the source and extract the relevant content for the post.

**Constraints:**
- If `source_note` is provided, you MUST read the full note
- You MUST classify the source up front as an **outline** (only bullets/section headings, no prose paragraphs) vs a **finished draft article**, and state the classification before proceeding — if it is an outline, the pipeline MUST write the full article from scratch, not merely format the existing text. Do not discover this mid-pipeline
- If the post builds on a single primary source (especially when it shares that source's title or core thesis), you MUST fetch the source's FULL content and assess overlap BEFORE drafting. If the draft would re-tell the source (same hook, anecdotes, quotes, examples), STOP, find a differentiated angle, and surface the derivative risk to the user proactively — do not wait to be asked "how unique is this?"
- If `source_url` is provided, you MUST fetch the article via `web_fetch` and extract key arguments, quotes, and structure
- If `source_url` is a YouTube link, you MUST use `yt-dlp` to extract the transcript (see ground-truth.md → YouTube Transcripts). Do NOT ask the user to paste title + description — try yt-dlp first
- If a fetch fails (SPA, paywall, auth-required), you MUST immediately suggest "File > Print > Save as PDF" as the extraction method rather than retrying with alternative approaches. Ask the user to share the PDF file — this reliably unlocks content from inaccessible pages
- You MUST identify the key arguments, quotes, and insights relevant to the user's focus
- If the user provided a focus or structure hints, you MUST prioritize content matching those
- You SHOULD extract 2-3 strong direct quotes from the source for potential use in the post

### 2. Follow the Reference Chain

Fetch articles linked from the source to build a richer reference base.

**Constraints:**
- You MUST identify links within the source article to related pieces (companion articles, referenced blog posts, research papers)
- You MUST fetch and summarize the most relevant linked articles (typically 2-4)
- You SHOULD prioritize links that are from the same series, directly support the argument, or provide counterpoints
- You MUST NOT follow more than 5 links because diminishing returns
- If any reference is a PDF (local or user-provided), you SHOULD offer to extract figures and embed them in the article with attribution. Figures from referenced papers/blogs significantly improve article quality — proactively surface this option rather than waiting for the user to ask

### 3. Find Own Prior Work

Search the author's published content for pieces that connect to the topic. **Optional** — this step runs only if the relevant config is set.

**Constraints:**
- Resolve `site_public_base_url` (`python3 scripts/content_paths.py get site_public_base_url`). If set, you SHOULD search that site for related posts; if empty, skip the website search.
- Resolve `prior_work_dir` (`python3 scripts/content_paths.py get prior_work_dir`). If set, you MUST grep that folder for related posts, articles, and drafts; if empty, skip the local search.
- You MUST identify pieces that can be naturally referenced in the new post (same topic, supporting argument, prior exploration of the theme)
- You SHOULD aim for 2-5 own references because it builds the author's body of work without being self-promotional
- When you identify own articles to reference, you MUST fetch their full content before writing any derivative content (summaries, references). Do NOT draft from titles or descriptions alone — this leads to inaccurate representations of the author's own work
- If neither config value is set, skip this step entirely and say so.

### 4. Find Workspace Connections (optional)

Search your workspace for related content that can inform the post.

**Constraints:**
- If a `workspace_root` is configured (beyond the bundled examples), you SHOULD grep it for keywords from the topic (product names, concepts, people)
- You SHOULD check any relevant notes: projects, research, prior meeting/topic notes
- You MUST NOT spend more than 3 grep calls because diminishing returns
- Workspace connections inform the writing but are NOT necessarily referenced in the published post — they provide context
- If no workspace beyond the examples is configured, skip this step.

### 5. Study Writing Style

Read the author's previous posts to match their voice and formatting patterns.

**Constraints:**
- You MUST read at least 3 posts from the configured style corpus: `python3 scripts/content_paths.py get style_corpus_dir`. (Ships pointing at the bundled synthesized example posts; the author repoints it at their real corpus.)
- You MUST identify recurring patterns: emoji usage, section headers (Unicode bold vs markdown), personal openers, call-to-action style, hashtag conventions, source citation style
- You MUST NOT invent a new style — match the author's established voice
- If the corpus is empty or unset, use a clear, plain, neutral voice and say so
- You SHOULD note which posts had the highest engagement (if that metadata exists) and lean toward that style

### 6. Research and Enrich

Connect the post topic to relevant AWS services, industry trends, or external context.

**Constraints:**
- If the user requests a connection to an AWS service or topic, you MUST do web research to find the relevant angle
- You MUST verify any factual claims via web search or AWS docs before including them because posts are public and attributed to the user
- You SHOULD search for specific blog posts or documentation on kiro.dev and aws.amazon.com when referencing Kiro or AWS features
- You SHOULD keep the AWS/product tie-in natural and relevant — it MUST NOT read like an ad
- You MAY suggest a tie-in if one is obvious, but you MUST ask the user before including it

### 7. Draft the Post

Write the post in Obsidian-flavored markdown and present it to the user.

**Constraints:**
- For type "linkedin-post", you MUST respect a 3,000 character limit for the final formatted version
- For type "post" or "article", there is no hard character limit — the user typically writes for their website and cross-posts as a LinkedIn article or generates a trimmed LinkedIn post version separately
- For type "article", you SHOULD aim for 5-15 minute read time
- You MUST include a personal opener that connects the user to the topic
- You MUST NOT write first-person anecdotes or specific timeframes (e.g., "A few weeks ago, I noticed...", "for months now") without confirming with the user that the experience is real because the user's name is on the content. Use vague/hedged language (e.g., "for quite some time") until confirmed
- You MUST use the section header style from the user's previous posts (typically emoji + Unicode bold for LinkedIn, `##` for website posts)
- You MUST use Unicode bold characters (𝗔𝗕𝗖, not **ABC**) for any text that will appear bold on LinkedIn — markdown bold does not render on LinkedIn. This applies to all LinkedIn teasers, posts, and article content
- You MUST include a call-to-action or question at the end
- You MUST add a Sources section with footnote-style references `[1]`, `[2]`, etc. — this includes both external sources AND the author's own prior work. All references go in the same numbered list at the bottom. Do NOT use inline hyperlinks for own prior work while using footnotes for external sources — consistency matters. **Emit each Sources entry as a Markdown list item (`- [N] [title](url) — note`) with a blank line before the list**, so it renders as a list rather than collapsing every entry into one paragraph. Use a `## Sources` heading (not a bold label) — the citation/AI-smell scanners key off the heading.
- You MUST add relevant hashtags (3-6, matching the user's typical count)
- You SHOULD include at least one strong direct quote from the source material
- You SHOULD reference own prior work where it naturally fits (from step 3)
- When using a named quote as a rhetorical anchor, you MUST verify the original source and attribution before embedding it. If the quote is well-known, search for the original speaker/context — do not attribute it to the nearest related reference. If the source is uncertain, flag it explicitly rather than guessing
- You MUST present the draft to the user and wait for feedback before proceeding
- Before creating the draft folder, you MUST check whether a draft already exists at the target slug; if one exists, read it and determine whether it is a placeholder/outline (safe to overwrite) or finished content (confirm with the user before overwriting) — this prevents accidental loss of content
- You MUST save the draft BEFORE presenting it — resolve the blog channel folder with `python3 scripts/content_paths.py channel-dir <date>-<slug> blog`, create it, save `post.md` there with frontmatter (`description`, `date`, `status: draft`, `type`, `based-on`, `tags`), and create an `assets/` subfolder at the item root. Then present a summary and offer to open it. Do NOT present the draft only inline without saving — the user expects to find it on disk immediately
- The `description` frontmatter field MUST be an SEO-ready meta description: max 155 characters, one or two complete sentences summarizing the post's main argument or topic, no double quotes inside the value (use single quotes if needed), wrapped in double quotes. This description is used as the HTML meta description for search engine snippets and OpenGraph/Twitter card previews when published to the website
- You MUST proactively identify content that would benefit from a structured diagram (timelines, comparisons, flows, hierarchies, matrices) and create Mermaid diagrams for them. Diagrams make complex relationships scannable and break up long text. Use Mermaid syntax (timeline, graph, flowchart, quadrantChart, etc.) embedded as fenced code blocks — these render natively in most markdown viewers and can be pre-rendered to SVG by your publish step.
- If your downstream publish step pre-renders diagrams and applies a width cap to the reading column, design with that in mind: prefer `flowchart TB` (a narrow, tall column) over `LR` (a wide band that a cap would shrink to illegibility), and keep node labels short enough to read at ~600px wide
- When embedding skill file excerpts or structured constraint blocks in blog posts, you MUST use `yaml` syntax highlighting (not `markdown`) — it renders with a lighter, more readable color scheme. Add an italic caption above each code block explaining what the reader is looking at
- When styling Mermaid nodes with custom colors, you MUST ensure text/background contrast is readable at small sizes. Avoid very dark backgrounds (#232f3e, #1a1a2e, #000) with white text — prefer medium-tone colors (#4a6fa5, #2d6a4f, #8c6bb1). For dark text, use light backgrounds (#ff9900 with #000, #e8e8e8 with #333). This prevents readability issues when diagrams are rendered to SVG for the website
- You SHOULD prefer diagrams over tables when the content has a temporal, hierarchical, or flow dimension
- You SHOULD NOT force diagrams where a simple list or paragraph suffices
- **If you render a diagram to a STANDALONE SVG asset** (e.g. a D2 diagram, or Mermaid rendered outside the inline fenced-block pipeline), you MUST save the **source file** (`.d2` / `.mmd`) in the draft `assets/` directory alongside the rendered `.svg`, named consistently (`diagram-01-foo.d2` + `diagram-01-foo.svg`). The source is needed for later edits (label widths, mock data). Inline Mermaid fenced blocks already retain their source in `post.md`, so this applies only to standalone renders.

### 8. Iterate on Draft

Incorporate user feedback until they approve the content.

**Constraints:**
- You MUST apply all requested changes
- For type "linkedin-post", you MUST re-check character count after each revision
- You MUST present the updated draft after each round of changes
- You MUST NOT proceed to formatting until the user explicitly approves the content
- When the user suggests adding more references, you MUST search for specific sources (blog posts, docs, own articles) rather than inventing generic citations
- If a clarification question (e.g., "which blog post to link?") goes unanswered for 2 user turns, you MUST make a best-effort decision, state the assumption explicitly, and move on. Do NOT repeat the same question across multiple turns — it wastes user attention and breaks flow
- Before presenting the draft as "ready for review", you MUST run a consistency check: (1) verify that numbers cited in prose match numbers in tables, (2) flag counts that appear in multiple places and ensure they agree, (3) flag time-relative language ("today", "two days ago", "yesterday", "this week") that will break if the publish date differs from the draft date because articles are often drafted weeks before publishing, (4) verify every source in the Sources section is referenced inline with [N] — unreferenced sources must either be cited or removed
- You MUST determine the publishing slot (date) BEFORE running the final review pass. Time-relative references ("earlier this week", "yesterday", "just announced") must be validated against the publishing date, not the drafting date. If the slot isn't decided yet, flag all time-relative language as needing adjustment

### 8b. Actionability Enrichment (Optional)

Review the draft for opportunities to make it more actionable and reference-worthy, without changing the narrative voice or essay structure.

**Constraints:**
- This step is OPTIONAL — it suggests enhancements, it does not rewrite the post
- You MUST NOT change the opener, tone, or narrative structure — those are the post's identity
- You MUST scan the draft and suggest additions in these categories:

| Category | When to suggest | Example |
|---|---|---|
| **Decision framework** | Post compares options, architectures, or approaches | Add a Mermaid flowchart at the end: "Which approach fits your situation?" |
| **Runnable code sample** | Post references an API, CLI command, or configuration | Add a copy-paste-ready code block (boto3, CLI, YAML) that the reader can try immediately |
| **Pricing/cost context** | Post discusses a service, architecture, or trade-off with cost implications | Add a ballpark cost comparison or link to the pricing page |
| **Scope/freshness disclaimer** | Post references preview features, beta APIs, or rapidly changing capabilities | Add a dated scope note: "This reflects the state as of [date]. Check [link] for the latest." |
| **Quick-reference table** | Post explains 3+ options, layers, or components in prose | Suggest a comparison table summarizing the key dimensions |

- You MUST present suggestions as a numbered list with: category, where in the post it would go, and a draft of the addition
- You MUST NOT add more than 3 enrichments per post — the goal is selective enhancement, not turning every essay into a reference guide
- The user decides which (if any) to include — do NOT apply them automatically
- If the post is pure thought leadership with no technical comparison or service reference, skip this step entirely and say so

### 9. Challenge and Improve

Generate challenging reader questions, answer them, and use the answers to strengthen the article.

**Constraints:**
- You MUST generate 10 challenging questions a critical reader might ask — covering methodology gaps, missing nuance, unstated assumptions, and alternative interpretations
- You MUST provide elaborated answers to each question — honest about limitations, with practical guidance
- You MUST save both questions and answers in a dedicated note (`challenging-questions.md`) at the item root
- You MUST then review the answers and identify insights that strengthen the article — typically 4-6 improvements
- You MUST weave those insights into the article proactively: acknowledge limitations upfront, add missing context, strengthen weak arguments, and address the sharpest critiques before readers raise them
- You MUST NOT make the article defensive — the tone should be honest and confident, not apologetic
- You SHOULD prioritize improvements that address: sample size / methodology caveats, unstated assumptions, missing comparisons to alternatives, and safety / failure mode implications
- You MUST present the changes to the user as a summary table (Q&A insight → what changed) before proceeding

### 10. Generate Reader FAQ

Create a standalone FAQ document anticipating questions readers will ask after reading the post.

**Constraints:**
- This is NOT the same as Challenge Questions (step 9). Challenge questions strengthen the article internally. The FAQ is an external-facing companion document for the author's review, LinkedIn comment responses, and potential talks
- You MUST generate 8-12 questions that a reader would naturally ask after reading the published post
- Questions SHOULD cover: "how does this compare to X?", "can I use this for Y?", "what about Z risk?", practical application questions, and "what's the connection to [related topic]?"
- Answers MUST reference both the blog post content AND the original source material (official announcements, papers, docs) with specific citations
- Answers SHOULD go deeper than the blog post itself — this is where the author's additional research pays off
- You MUST save as `faq.md` at the item root
- You MUST include a Sources section at the bottom listing all referenced materials

### 11. AI Smell Check

Scan the draft for common tells of AI-generated text and fix them. This step has two halves: a **deterministic script** for the mechanical, regex-detectable tells (run first), then an **LLM semantic pass** for the judgment calls the script cannot make.

> [!important] Enhanced pipeline is canonical
> Run this step **via the `humanize-pipeline` skill** (`.kiro/skills/humanize-pipeline/`) — it is the standard humanization gate for every new post. It layers: **(1)** this deterministic scanner as the pre-pass, **(2)** a voice-calibrated rewrite against your voice profile (`voice_profile_path` in `config/pipeline.local.json` — the author's calibrated voice, not a generic humanizer), **(3)** a deterministic re-scan gate (the rewrite can re-introduce mechanical tells), **(4)** an independent-model critic pass via the MCP-free `.kiro/agents/critic.json` agent on a DIFFERENT model than the drafter (required for rigorous-technical and product-launch posts; best-effort otherwise), **(5)** detector telemetry (advisory). The scanner run and the judgment-call category list below ARE stages 1/3 — keep them; the pipeline adds the calibrated rewrite (2) and independent review (4). Persist `ai-smell.md` exactly as specified below. Known false positives to preserve, never "fix": quoted AI-cliché examples, domain terms (e.g. "energy landscape", "syntax highlighting"), quoted regulatory text, and words inside URLs/titles.

**Constraints:**
- You MUST FIRST run the deterministic scanner over the draft and paste its output before doing the prose pass. This catches the mechanical tells (citation-markup artifacts, em-dash count, banned vocabulary, curly quotes, Title Case headings, negative parallelisms, copula avoidance, "Challenges/Future" outline conclusions, bold-sentence headers) with real counts and line numbers, so they cannot be silently skipped by an LLM grading its own output:
  ```bash
  python3 scripts/ai_smell_scan.py <draft>/post.md
  ```
  (Path is relative to the repo root; the script is stdlib-only, no install needed.)
  - The script tiers findings: **ARTIFACT** (hard gate — citation-markup junk like `utm_source=chatgpt.com`, `turn0search0`, `:contentReference`, `oaicite`, placeholder dates, `[Your Name]`; the script exits non-zero) → you MUST fix every ARTIFACT before proceeding. **SIGNAL** (real tells — review and fix or consciously keep). **STYLE** (curly quotes, Title Case headings — this author's house style / weak signals; informational, do NOT mass-correct).
  - Treat the script's counts as ground truth for em-dashes and vocabulary (replaces the eyeballed thresholds below). Then do the semantic pass on what the script cannot judge.
- After the script, you MUST read the entire post in one pass, identify ALL instances of each judgment-call category below, and fix them in a single write operation. Do not patch one occurrence at a time — incremental patching leads to missed instances and re-runs
- You MUST scan the draft (excluding code blocks) for the following categories:
  - **Em dashes (—):** Use the script's prose count. More than ~10 in a 2,500-word article is a red flag. Replace excess with commas, periods, colons, or parentheses. Keep ~5-8 for natural emphasis
  - **AI vocabulary:** Flag words like "delve", "tapestry", "landscape", "leverage", "robust", "facilitate", "seamlessly", "elevate", "comprehensive", "straightforward", "fascinating", "remarkable", "groundbreaking", "nuanced", "navigate", "paradigm", "holistic", "intricate", "cornerstone", "testament" (plus era drift: "underscore", "pivotal", "vibrant", "showcase", "emphasizing", "highlighting", "showcasing"). Replace with simpler alternatives. Exception: "harness" is OK when used as a technical noun (agent harness, test harness)
  - **Negative parallelisms:** "not just X, but Y", "not only X, but Y", "it's not X, it's Y" — the script flags these; rewrite the strongest ones into a direct statement
  - **Copula avoidance:** "serves as", "stands as", "represents a", "boasts", "showcases" where a plain "is/are/has" reads better — the script flags these
  - **"Challenges / Future prospects" outline conclusions:** "Despite its X, faces challenges…", "only time will tell" — rewrite as a concrete, honest closing
  - **Bold sentence headers:** The pattern `**Bold phrase.** Rest of sentence...` is a recognizable ChatGPT habit. Restructure as regular paragraphs or use `###` subheadings instead
  - **Significance inflation:** Flag "monumental", "transformative", "game-changing", "revolutionary", "unprecedented", "seismic shift". Replace with measured language backed by evidence
  - **Transition word overuse:** Flag "Furthermore", "Additionally", "Moreover", "It is important to note", "This highlights", "In today's world", "It goes without saying", "At the end of the day". More than 1 per section is a tell
  - **Excessive hedging:** Flag "studies suggest", "experts believe", "it could be argued", "many would agree" without named sources. Either cite a source or state an opinion directly
  - **Filler phrases:** Flag "It is important to note that", "This highlights the importance of", "It cannot be overstated", "When all is said and done". Remove or rework
  - **Template intros:** "In today's rapidly evolving..." — rewrite with specific, concrete openers
  - **Hollow conclusions:** "Ultimately, a balanced approach..." — replace with actionable or honest statements
  - **Sentence length uniformity:** Use the script's mean/StdDev. Monotonous rhythm is a tell (aim StdDev > 5 words)
  - **Paragraph length uniformity:** Use the script's mean/StdDev. Uniform 4-6 sentence paragraphs are a tell (aim StdDev > 10 words)
  - **Rule of threes overuse:** "A, B, and C" repeated throughout — vary enumeration patterns
  - **Collaborative language leaks:** Flag "I hope this helps", "Let me know if you'd like", "Feel free to" in published prose — these are chatbot patterns
- You MUST NOT mass-correct STYLE findings (curly quotes, Title Case headings) — those are the author's deliberate house style, not AI tells. The Wikipedia guide explicitly warns that no single sign is proof and lists "ineffective indicators" (perfect grammar, formal style, transition words in isolation). Do not strip the author's real voice
- You MUST present a summary table of findings (category, count, examples, fix) before applying changes — include the script's ARTIFACT/SIGNAL/STYLE breakdown
- You MUST apply all fixes, then re-run the script to confirm 0 ARTIFACT findings and that SIGNAL counts dropped to acceptable levels
- You SHOULD aim for: 0 ARTIFACT, <10 em dashes in prose, 0 AI vocabulary words, 0 bold sentence headers, 0 significance inflation, 0 filler phrases, good sentence and paragraph length variance
- **PERSIST the result (MANDATORY artifact).** You MUST save an `ai-smell.md` report at the item root (next to `faq.md`/`challenging-questions.md`), containing: the deterministic scanner's final output (re-run after fixes — paste the ARTIFACT/SIGNAL/STYLE counts and any remaining findings) AND a short prose-pass summary (the judgment-call categories you reviewed and what you changed). This is a required draft artifact — a draft is not review-ready without it. Write it even in multi-post runs; do not run the gate and discard the output.

### 11b. Critical Reader Pass

Read the post as someone who wasn't there. Identify clarity and coherence issues that the challenging questions step doesn't catch.

**Constraints:**
- You MUST FIRST run a bidirectional Sources↔citation check: every entry in the Sources list MUST appear as an inline `[N]` citation, and every inline `[N]` MUST have a Sources entry. Fix orphaned Sources entries (cite inline or remove) and orphaned citations before the rest of the pass — do not defer this to a later edit round
- You MUST read the full post and list issues where a reader outside the author's context would stumble
- You MUST check for: undefined terms or jargon used without context, unclear antecedents ("we" without stating who), broken paragraph transitions (double "But", orphaned connectors), unreferenced sources (listed but never cited inline), vague descriptions that assume reader knowledge they don't have, claims that need grounding (numbers stated as fact vs. "for example")
- You MUST present findings as a numbered list with the problematic text and a suggested fix
- You MUST get user approval on which items to fix before applying changes
- This step catches different issues than Challenge Questions (step 9): challenges test argument strength, this tests communication clarity

### 11c. Generate TL;DR

Add a concise summary for time-pressed readers at the top of the post.

**Constraints:**
- You MUST add a blockquote TL;DR immediately after the title (before the first section heading)
- The TL;DR MUST be 3-5 sentences covering: what happened, the key insight, and the main takeaway
- The TL;DR MUST accurately reflect the final post content (run this after all edits are complete)
- You MUST NOT use the TL;DR as a teaser — it should give the full conclusion so busy readers get value without reading the full post
- Format in the draft (Obsidian-flavored markdown): `> **TL;DR:** [summary text]`
- NOTE: keep the `> **TL;DR:**` blockquote form in the draft (it renders in standard markdown). If your downstream publish step has a dedicated TL;DR component/shortcode, the conversion happens there — not in this pipeline.

### 11d. Claim & Reference Verification (WARN-ONLY gate)

Verify that the post's citations exist and actually support the claims they back. This is the *substance* gate — distinct from the *style* gate in Step 11 (AI smell). It operationalizes the mandate in `ground-truth.md` ("Do NOT present product/feature claims… until you have fetched at least one official doc source in the same turn") and implements Bryan Dollery's claim+reference-checking agent. The step has a **deterministic harness** (a script) and an **LLM judgment sub-step** (you).

> [!important] MANDATORY — always run
> This gate ALWAYS runs before a post is publish-ready (not optional). Two parts are HARD gates: (1) the **internal-leak scan** (`leak_scan.py`) — any internal marker BLOCKS publish; (2) **reference existence**. The claim↔source SUPPORT judgment and the legal-claim review are best-effort/semantic — flag confidence rather than asserting certainty, but every NOT_SUPPORTED / leak / unverified item lands on a must-fix list AND a written `claim-verification.md` report.
>
> **P1 (NOT built yet):** thesis-coherence checking (Bryan's agent 2). Step 9 (challenge questions) partially approximates it.

**Constraints:**
- You MUST FIRST run the deterministic verification harness over the draft and paste its output:
  ```bash
  python3 scripts/verify_citations.py --json --fetch <draft>/post.md
  ```
  (stdlib-only; `--fetch` pulls a text excerpt of each external source so you can judge support; drop `--fetch` or add `--no-external` for offline/headless runs.) The harness does the parts a script can do honestly:
  - **Reference existence** — every inline `[N]` resolves to a Sources entry; every external source URL resolves (curl); relative links are left to your downstream publish step's link checker; orphan and no-url sources are flagged.
  - **Support worklist** — for every inline citation it extracts the carrying sentence (the claim), pairs it with the source `{title, url}` and a fetched excerpt, and marks it `NEEDS_LLM_JUDGMENT`.
  - **Uncited factual claims** — an advisory heuristic flags sentences asserting product behavior, availability, version numbers, quotas, pricing, or percentages that carry NO citation. Each of these MUST either get a source or be softened to clearly-marked opinion.
- You MUST then perform the **LLM support judgment** on the worklist: for each claim↔source pair, read the claim and the source excerpt (fetch the full source if the excerpt is insufficient) and decide whether the source supports the claim **on the whole** (not via one cherry-picked sentence). Record a verdict per pair: SUPPORTED / PARTIAL / NOT_SUPPORTED / UNCLEAR, and **state your confidence**. (Optional automation: pass `--judge-cmd "<llm-cmd>"` to have the harness pipe each item to an external judge; treat its verdicts as advisory.)
- For any **NOT_SUPPORTED** or **UNCLEAR** verdict you MUST either fix the citation (find a source that supports the claim), soften the claim, or — for time-boxed/headless runs — mark it `unverified — human review required` in your findings rather than silently passing. Honor the trust hierarchy in `ground-truth.md` (official docs > community > your notes > LLM memory).
- You MUST present a findings table: `Claim → Citation → exists? → supports? (verdict + confidence) → action`.
- You MUST run the deterministic **internal-leak scan** and paste its output — a HARD gate (exit 1 = BLOCK publish), because the post is public:
  ```bash
  python3 scripts/leak_scan.py <draft>/post.md --aliases "$(python3 scripts/content_paths.py aliases)"
  ```
  It flags internal-only markers in the text (internal-org emails, internal chat/wiki/tool links, internal hostnames, 12-digit cloud account IDs, personal `/Users/` paths, and any aliases you supply via config). Public references (official docs and product names) are NOT flagged. Fix every finding before publishing. Built-in patterns are org-neutral; add YOUR organization's markers by copying `config/leak-patterns.sample.json` to `config/leak-patterns.local.json` (gitignored) — see `CONFIGURATION.md`.
- You MUST enumerate EVERY material claim — not only the cited ones — walking the post section by section, and classify each: **[EXTERNAL]** (verifiable from a public doc — give the URL) / **[FIRST-PARTY]** (your own demo/result — acceptable only if framed as "in my run", not universal fact) / **[INTERNAL-DERIVED]** (knowable only from internal/private sources or your own un-published testing — if it has no public source it is a LEAK RISK: re-ground to a public source, soften to "in my testing", or remove) / **[OPINION]**.
- **Legal-implication claims get extra scrutiny.** Flag and verify each (data retention, residency, who-can-access, GDPR/regulatory, pricing, security guarantees) against an official source; over-claims here are the highest risk. If a public source doesn't fully support it, soften or caveat — do not assert.
- You MUST write the audit to `<item-root>/claim-verification.md` (at the item root, next to `faq.md`/`challenging-questions.md`) — a required artifact EVERY time (a draft is not review-ready without it). It MUST contain: a verdict summary (publish-safe?), the per-claim table (Claim | Type | Correct? | Reasoning | External source | Leak/Action), a must-fix list (every leak / NOT_SUPPORTED / unverified / over-claim + its fix), and an explicit internal-leak yes/no audit. Write it even in multi-post runs — running the harness and discarding the report does NOT satisfy this step.
- You MUST run the AI-attribution check and add a statement if missing (transparency, per Bryan's agent 4):
  ```bash
  python3 scripts/ai_attribution.py --check <draft>/post.md
  python3 scripts/ai_attribution.py --emit   # template to paste
  ```
  Adding the statement is OPTIONAL and the author's call on placement/wording — the helper only makes its absence visible and offers a template; it never edits the post.

### 11e. Visual QA (blog images — MANDATORY artifact)

Verify the post's images are coherent: the hero/featured image is declared and resolvable, every inline figure points to a real asset, nothing is duplicated, and figures carry alt text. This is the *visual* gate — distinct from the style (Step 11) and substance (Step 11d) gates. It has a deterministic harness (a script) and is persisted as a required artifact.

**Constraints:**
- You MUST run the deterministic visual-QA harness over the draft and paste its output, then persist the report:
  ```bash
  python3 scripts/visual_qa.py <item-root>/blog/post.md --write
  ```
  (stdlib-only; `--write` saves `visual-qa.md` at the item root next to `faq.md`/`claim-verification.md`.) It checks, deterministically: hero/`featured_image` declared + the file resolves (cover is assigned at publish, so a not-yet-renamed cover is a warning, not a block); every inline image reference (Hugo `{{< figure >}}`, markdown `![]()`, Obsidian `![[ ]]`) resolves to a file in `assets/`; no image is embedded twice; figures carry alt text (wikilink embeds warn — alt is added at publish; `{{< figure >}}`/markdown without alt are issues); and orphan assets never referenced in the body (advisory).
- `visual-qa.md` is a REQUIRED draft artifact. Write it even in multi-post runs.
- The harness is WARN-ONLY by default; fix every **Issue** it lists (missing referenced file, duplicate embed, missing-alt on a published figure form, hero declared but assets/ empty) before publishing. Warnings are advisory.

### 12. Generate Image Prompts

Create 3-4 image generation prompt options. (This pipeline produces prompts only — image *generation* is your own downstream, BYO-tool step.)

**Constraints:**
- Before writing prompts, if the post contains code blocks, architecture references, CLI commands, or sample outputs: you MUST apply the checks from `pre-publish-safety.md` to the post content (secrets/credentials, internal-org references, personal paths, real account IDs, real company names paired with fabricated data). Fix any findings before proceeding.
- This pipeline does NOT generate images — it produces prompt text. If the user wants images, they paste the prompts into their own image tool. Do not assume a specific generator.
- You MUST read the configured image guidelines before writing prompts: `python3 scripts/content_paths.py get image_guidelines_path`. Apply its guidance to every prompt. (Ships pointing at a generic example; the author repoints it at their own performance-derived guidance. If unset, use the general guidance below.)
- You MUST create at least 3 prompt options with different visual angles on the post's theme
- You MUST phrase each as an explicit generation request ("Generate an image: …") so it works with instruction-following image models
- You MUST NOT include text overlays in the prompts because AI image models render text poorly
- You MUST NOT use special characters ($, %, &, #, !) in suggested image filenames — use plain words (e.g., "The 20 Dollar Breach" not "The $20 Breach"), because special characters break some markdown image embeds and URL encoding
- You SHOULD include one option that incorporates the personal context from the opener
- You MUST save the prompts as `image-prompts.md` at the item root
- Each prompt SHOULD describe: subject, environment, lighting, style, and camera framing
- **General image guidance (if no guidelines file is configured):**
  - PREFER: human presence, warm/natural lighting, story-telling composition, authentic/editorial feel, workspace scenes
  - AVOID: dark neon "tech" aesthetic, infographic-style text overlays, overly literal metaphors, generic stock-cyber imagery
  - The image SHOULD match the post's narrative arc, not just its topic

## Examples

### Website Post from an External Article

```
User: "write a post about https://martinfowler.com/articles/... focusing on code quality"
Agent: [fetches article, extracts key arguments and quotes]
       [follows reference chain — fetches linked articles]
       [searches configured prior-work sources for own related articles (if set)]
       [greps the workspace for related context (if configured)]
       [reads 3 posts from the style corpus for voice]
       [drafts post with personal opener, references, structured sections]
       [user iterates on draft]
       [generates 10 challenging reader questions + answers; weaves insights back in]
       [runs AI-smell, claim/leak verification, visual QA gates — persists reports]
       [generates 3 image prompt options → image-prompts.md]
       [saves all artifacts at the item root]
```

### Short-Form Social Post

```
User: "write a linkedin-post about [[some-source-note]] focusing on the agentic coding part"
Agent: [reads the source note, extracts the relevant angle]
       [reads 3 posts from the style corpus for voice]
       [drafts post ≤3,000 chars with personal opener, key quotes]
       [user iterates on draft]
       [generates 10 challenging questions + answers, improves post]
       [saves artifacts]
```

## Path configuration

Paths are NOT hardcoded. They resolve through `config/content-paths.local.json` (+ `pipeline.local.json`
for non-path values) via the helper `scripts/content_paths.py`. This skill relies on **content_root**
(per-item draft folders), **style_corpus_dir** (voice matching), and **image_guidelines_path** (Step 12).

Resolve at runtime instead of restating an absolute path:

```bash
python3 scripts/content_paths.py get content_root            # per-item drafts root
python3 scripts/content_paths.py get style_corpus_dir        # prior posts for voice
python3 scripts/content_paths.py get image_guidelines_path   # Step 12 guidance
python3 scripts/content_paths.py item-dir <date>-<slug>      # one content-item folder
python3 scripts/content_paths.py channel-dir <date>-<slug> blog   # a channel subfolder
python3 scripts/content_paths.py aliases                     # leak-scan aliases
```

A folder move/rename is a one-line edit in the config — never reintroduce hardcoded paths here.

## Item-folder layout + content-item.md manifest

### Per-item folder layout (the convention for NEW items)

Each content-item draft folder under `content_root` uses channel subfolders, with SHARED
material hoisted at the item root:

```
<date>-<slug>/
├── content-item.md          # cross-channel status manifest (see schema below)
├── ideation.md              # the finalized Definition-of-Ready (from ideation-session)
├── faq.md                   # shared quality material (hoisted)
├── challenging-questions.md # shared
├── ai-smell.md · claim-verification.md · visual-qa.md   # persisted gate reports
├── image-prompts.md         # shared (when present)
├── assets/                  # shared images/diagrams
├── blog/      post.md       # blog channel — the draft
└── linkedin/  (optional)    # social channel (only if you produce a teaser downstream)
```

Resolve channel subfolders via the config, never hardcode:
`python3 scripts/content_paths.py channel-dir <date>-<slug> {blog|linkedin}`.

### content-item.md manifest schema (one per item folder)

```yaml
---
description: "Cross-channel content manifest: <title> — ..."
type: content-item
title: "<real post title>"
slug: <slug>
item_folder: <date>-<slug>
tldr: "<one-line TL;DR>"
channels:
  blog:     { status: draft|final, source: blog/post.md }
  linkedin: { status: draft|n/a,   teaser: linkedin/linkedin-teaser.txt }
updated: <YYYY-MM-DD>
---
```

### This skill's manifest responsibility

post-creation CREATES the item folder in this layout and writes the INITIAL `content-item.md`
(title, slug, tldr, channels in their starting state: blog=draft). Use
`content_paths.py channel-dir`/`item-dir`/`manifest` to place files.

---
## Hardening rules (synced from upstream, 2026-08)

### Sources Block Must Use `## Sources` Heading
The Sources block MUST be a `## Sources` markdown heading — never a bold label (`**Sources:**`). The citation-verification scanner and AI-smell parser key off the heading; a bold label reports all citations undefined and triggers an AI-smell signal.

### A "Verified" Claim-Ledger Verdict REQUIRES a Quoted Excerpt (HIGH)

Any `Verified` / `SUPPORTED` verdict in `claim-verification.md`, a fact-check report, or an
independent-model critique MUST carry a **verbatim short quote from the fetched source** that
supports the claim.

- A verdict without a quote is treated as **Unverified** by every downstream gate.
- The quote requirement exists because it forces the verifier to read the actual sentence instead of
  pattern-matching the page title. (Real-world failure: a citation was recorded "Verified" in two
  separate gate artifacts while the cited page said the *opposite* — both gates had matched the
  topic, not the claim, and a live factual error shipped.)

### Independent-Model Claim Review Is MANDATORY for Product-Launch Posts (HIGH)

The independent-model gate (the MCP-free `.kiro/agents/critic.json` agent on a model DIFFERENT
from the drafter — see humanize-pipeline stage 4) is **required, not optional**, for any post
whose primary subject is a product launch, GA announcement, or preview feature, and for any post
making load-bearing technical-rigor claims.

- The gate must run on **the exact prose that ships**, not an earlier draft.
- Re-verification of availability/scope claims must **fetch the live authoritative source in the
  same turn** the claim is evaluated.
- Same-model self-review does NOT satisfy this — a same-model gate has confirmed a wrong
  region count as "verified" that the independent model caught.
- If the independent gate cannot run, FAIL LOUDLY: mark it NOT SATISFIED as a headline in your
  run report. Never silently substitute a same-model pass.

### Citations: Insert Inline `[N]` Markers BEFORE the Bidirectionality Scan

Run the orphaned-sources / uncited-claims scan (Step 11b first constraint, and
`verify_citations.py`) **after** markers exist. Correct order:
1. draft with inline `[N]` markers as each claim is written (preferred), or
2. draft, then insert all markers, **then** scan.

Scanning a marker-less draft reports every source as orphaned — noise that hides real gaps.

### AI-Smell Gate: Documented Exemption for Verbatim Quotes

The overused-word check must distinguish **agent-authored prose** from **verbatim quotes** (a
researcher's words, a doc excerpt, a customer statement). Quotes MUST NOT be reworded to satisfy a
regex.

- Compute the overuse count over agent-authored prose only, excluding blockquotes and quoted spans.
- If a flagged term's count is driven by quotes, record a one-line exemption in the gate artifact
  (e.g. `"landscape" ×15 — 9 in verbatim quotes, exempt`) and move on.
- Do not spend cycles trying to lower a quote-driven count. Document the exemption immediately.

### Image-Content QA: Visuals Must Match the Post's Semantics

Visual QA (Step 11e) is deterministic only (renders, layout, file presence) — nothing checks
whether an image's *content* is semantically accurate. When reviewing generated or supplied
visuals, add a content check:

- Do numbers/scores/labels shown correspond to something the described product or system actually
  produces? (Real-world failure: an image showed a percentage confidence score with a green check
  while the product returns *categorical* confidence levels — and the post itself warned against
  exactly that rubber-stamp framing.)
- Does the visual contradict the post's argument?

### Diagram Orientation: Probe the Aspect Ratio Before Accepting a Render

When a post includes a rendered diagram, compute the rendered aspect ratio during the diagram
phase. If `width/height > ~5`, switch the layout from left-to-right to top-to-bottom, update the
diagram source to match, and note it. Proactive, not a reactive fix after seeing an illegible
strip at article width.
