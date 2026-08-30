# Writing Guardrails

Guardrails for producing honest, in-voice content. These shape the ideation angle and the draft. They are intentionally generic — adapt the optional rules to your own employer/publishing policy.

## Match the author's voice — don't invent one

- Read at least 3 of the author's prior posts (from `style_corpus_dir`) before drafting. Identify recurring patterns: openers, section-header style, emoji use, citation style, call-to-action style.
- Match the established voice. Do NOT impose a new style. If no corpus is configured, use a clear, plain, neutral voice and say so.

## No fabricated first-person claims

- Never write first-person anecdotes or specific timeframes ("a few weeks ago I noticed…", "for months now") unless the author confirms the experience is real. The author's name is on the content.
- Until confirmed, use hedged/vague language ("for some time") or drop the claim.

## No fabricated data; fictional names in examples

- Never pair a real company/person/product name with invented metrics, quotes, or claims.
- Use clearly fictional names for all sample/demo data. If a real entity must be referenced for a factual point, the fact must be accurate and sourced.

## Feature the code repo in every derivative (when one is featured)

- If the ideation draft marks a repo as *featured*, every derivative (the post and any teaser/video) must surface it: name it and link it. A featured repo missing from a derivative is an incomplete derivative.

## Framing of tools, vendors, and platforms you build on

- Present the architecture and the tools/services you build on **neutrally or positively** — describe what runs where as a factual capability, not a liability to be contained.
- Avoid defensive/negative framing of a platform or managed service the design already relies on (e.g. needless "privacy hedging" where the service handles data appropriately). Graceful offline/local behavior is fine to mention as good engineering, not as a virtue against the platform.
- *(Optional / adapt to your context: if you work for a vendor, do not disparage that vendor's own products in published content.)*

## Competitor products & third-party organizations

- **Competitor products:** default to generic terms ("other cloud providers", "AI coding tools") rather than naming competitors promotionally. Name a competitor only when factual accuracy requires it (e.g. citing a study that used it). *(Adapt to your employer's policy.)*
- **Third-party organizations** (vendors, agencies, brands not the subject or a cited source): default to generic references ("the vendor", "the airline") unless you deliberately choose to name them.

## Shareable artifacts: strip third-party branding

- When producing a shareable export (PDF, image, post) from externally-fetched content, strip third-party branding (site names, logos, URLs) by default unless you intend to credit the source. Also strip any content captured without the subject's consent, and neutralize textual pointers to it.

## Suppress needless hedging & AI tells

- These are enforced mechanically by the AI-smell gate in `post-creation`. At the writing stage: prefer plain statements over hedging ("studies suggest", "it could be argued") unless a named source backs it; vary sentence/paragraph rhythm; avoid template intros and hollow conclusions.

## Independent second opinion for rigorous claims

- For posts making load-bearing technical claims — and always for posts whose primary subject is
  a product launch, GA announcement, or preview feature — run a critical-reader review on a
  **different model** than the one that drafted the post (the MCP-free `.kiro/agents/critic.json`
  agent, invoked with an explicit `--model` override; see humanize-pipeline stage 4 and the
  `content-critique` skill).
- A same-model self-review does NOT satisfy this: the drafting model is blind to its own
  systematic errors, and same-model gates have confirmed factually wrong claims as "verified".
- If the independent review cannot run, **fail loudly**: mark the gate NOT SATISFIED as a headline
  in the run report. Never silently downgrade to a same-model pass and present the gate as passed.

## Preserve the author's voice through the AI-smell gate

- Run the humanization step voice-calibrated (see the `humanize-pipeline` skill and its
  `voice/VOICE.md` profile). The goal is removing AI tells, not flattening the author into a
  generic "de-AI'd" register. The voice profile legitimately overrides generic humanizer rules
  where they conflict.
- Verbatim quotes (a researcher's words, a doc excerpt, a customer statement) are never reworded
  to satisfy a style rule — document an exemption in the gate artifact instead.
