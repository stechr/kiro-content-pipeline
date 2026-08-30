# Ground Truth

How to keep published content factually honest. LLM training data and your own notes both go stale — verify before you assert.

## Core rule

Neither your notes nor LLM memory are ground truth for product/feature/API claims. Both drift — notes from prior sessions, training data from the knowledge cutoff. Verify against an authoritative source before presenting a claim.

## Hard constraint

**Do NOT present a product/feature/API/pricing claim to the reader until you have fetched at least one official source in the same session.** This holds regardless of where the claim came from (memory, notes, a forum). If sources are unavailable or inconclusive, say so explicitly rather than presenting unverified content as fact.

**Do NOT summarize or write derivative content about a source without fetching its full content first.** Titles and search snippets are insufficient — misrepresenting a source (especially the author's own prior work) is a factual-integrity failure.

## Honesty about depth

Never imply you read, analyzed, or reviewed content you did not actually fetch and process.

- If working from a snippet or preview, say so ("based on the search preview…").
- If asked to curate/rank/select from a set, fetch the full content of candidates first — or state the limitation upfront.
- The test: if asked "which ones did you actually read in full?", the answer should never be embarrassing.

## Trust hierarchy

Use the highest-authority source available for each claim type.

| Tier | Source | Strength | Weakness |
|------|--------|----------|----------|
| 1 | **Official docs / vendor reference** | Authoritative, versioned | Can lag new releases |
| 2 | **Vendor blogs / reputable community** | Timely, practical | Opinion mixed with fact |
| 3 | **Your own notes** | Curated, searchable | Stale if unmaintained |
| 4 | **LLM memory** | Always available | Knowledge cutoff, confidently wrong |

Prefer official provider sources over third-party aggregators (which are frequently outdated). If the official source is inaccessible, flag the claim as unverified.

## Verify computed facts

Never assert a computed fact — day-of-week for a date, timezone offset, arithmetic — without verifying it with a tool (`date`, a calculator). This matters most for anything dated in the content (publish dates, "earlier this week"): validate against the intended publish date, not the drafting date.

## Known-inaccessible sources

Some sources block automated fetching. Don't retry endlessly:
- **YouTube:** use `yt-dlp` to extract the transcript rather than scraping the page.
- **Auth-gated / SPA pages:** ask the user to "Print → Save as PDF" and share the file, rather than retrying fetch variants.
