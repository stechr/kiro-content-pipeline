---
description: "Generic image-prompt guidelines for post hero/feature images. Replace with your own performance-derived guidance."
---

# Image Prompt Guidelines

Guidance for the image *prompts* produced in post-creation Step 12. This is a generic starting point — replace it with your own guidance (e.g. derived from what performs well for your audience) by pointing `image_guidelines_path` at your own file.

## Prefer

- **Human presence** — a person in a scene reads as authentic and stops the scroll.
- **Warm, natural lighting** — feels editorial, not synthetic.
- **A story, not a symbol** — a concrete moment (someone at a desk mid-thought) beats an abstract metaphor.
- **Workspace / real-world scenes** — relatable context over sci-fi.
- **One clear subject** — a single focal point reads at thumbnail size.

## Avoid

- **Dark neon "tech" clichés** — glowing circuits, matrix rain, faceless hoodies. They blend into every feed.
- **Text baked into the image** — AI models render text poorly; keep words out of the prompt.
- **Over-literal metaphors** — a literal "pipeline" of pipes, a glowing shield for "security".
- **Generic stock-photo energy** — handshakes, lightbulbs, arrows going up.

## Prompt shape

Each prompt should describe, in order: **subject → environment → lighting → style → camera framing.** Phrase it as an explicit request:

> Generate an image: a developer at a wooden desk in warm afternoon light, looking up from a laptop mid-thought, shallow depth of field, editorial photography style, medium close-up.

## Filenames

No special characters (`$ % & # !`) in suggested filenames — they break some markdown image embeds and URL encoding. Use plain words: `desk-afternoon-thought.png`, not `$desk!.png`.
