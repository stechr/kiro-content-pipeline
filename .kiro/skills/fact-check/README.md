# fact-check

Pre-publication claim verification for any public-facing artifact — catches wrong facts, unverifiable claims, and internal-knowledge leaks before you publish.

## Why it exists

The secrets/PII scan in `pre-publish-safety.md` catches credentials and paths, but not *knowledge* problems: a claim that's wrong, or one that's only knowable from internal chat/private docs/spikes yet stated as public fact (a leak). This skill operationalizes the "Knowledge-Leak & Claim-Type Audit" rule into a repeatable pipeline: enumerate every material claim → classify (External / First-party / Internal-derived / Opinion) → flag leak risk → verify load-bearing + legal claims against official sources → produce a verdict + must-fix list.

## How to use it

- "fact-check this blog post before I publish"
- "leak check this LinkedIn draft"
- "verify the claims in this article against official sources"

Give it the draft path or URL; it returns a SAFE/FIX-REQUIRED verdict with a claims table and a must-fix list.
