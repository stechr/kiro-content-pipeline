---
name: fact-check
description: "Pre-publication claim verification for any public-facing artifact (blog post, article, LinkedIn post, customer-facing doc). Enumerates every material claim, classifies each by type (External / First-party / Internal-derived / Opinion), flags knowledge-leak risk, verifies load-bearing claims against official sources with extra scrutiny for legal-implication claims, and produces a structured verdict + must-fix list. Use when user says 'fact-check', 'claim check', 'verify claims', 'is this safe to publish', 'leak check', or before publishing any external content."
requires:
  steering:
    - pre-publish-safety.md
    - ground-truth.md
---

# Fact-Check (Pre-Publication Claim Verification)

## Overview

Verifies the factual integrity and leak-safety of a public-facing artifact before it ships. Distinct from the secrets/PII scan in `pre-publish-safety.md` (which catches credentials/paths) — this catches **knowledge** problems: wrong facts, unverifiable claims, and claims that are only knowable from internal sources but stated as public fact.

This skill operationalizes the "Knowledge-Leak & Claim-Type Audit" rule in `pre-publish-safety.md`. Read that section first — this skill is its execution procedure, and the two MUST stay in sync.

## Parameters

- **artifact_path** (required): Path or URL of the content to verify (markdown draft, published URL, post text).
- **citation_harness** (optional): Path to a citation/link-check script to run first, if the project has one.

## Workflow

### 1. Ingest the Full Artifact

Read the complete artifact — never work from a title, summary, or excerpt.

**Constraints:**
- You MUST fetch and read the FULL content because verifying claims from a summary misrepresents the work (see ground-truth.md "Honesty About Depth").
- If `citation_harness` is provided, you SHOULD run it first to surface broken/missing citations before manual review.

### 2. Enumerate ALL Material Claims

List every material factual assertion — not only the ones that already carry a citation.

**Constraints:**
- You MUST walk the artifact section-by-section and enumerate EVERY material claim, because cited claims are usually the safe ones; the risk lives in the uncited assertions.
- You MUST NOT limit enumeration to claims that already have links.
- You SHOULD record each claim with its location (section/line) for the report.

### 3. Classify Each Claim by Type

Assign every claim one of four types and a leak-risk flag.

| Type | Meaning | Action |
|------|---------|--------|
| **EXTERNAL / public** | Has (or can have) a public citation | Verify + cite |
| **FIRST-PARTY** | "In my testing…" framing | OK if true |
| **INTERNAL-DERIVED** | Knowable only from internal sources (internal chat, private docs/spikes, internal systems) but stated as universal fact with no public citation | **LEAK RISK** |
| **OPINION** | Clearly framed as opinion | OK |

**LEAK RISK definition:** a claim that is knowable only from internal/private sources and has no public grounding, presented as universal fact. Fix by (a) finding + citing a public source, (b) reframing as "in my testing…", or (c) removing.

**Constraints:**
- You MUST tag every INTERNAL-DERIVED claim as a LEAK RISK unless it is reframed or publicly grounded.
- You MUST give **legal-implication claims** (data-retention windows, data-residency, "data stays in your environment", human-review access, compliance/regulatory statements) EXTRA scrutiny and verify each precisely against a public source.

### 4. Verify Load-Bearing Claims

Fetch official sources for the claims that carry the most weight.

**Constraints:**
- You MUST verify EXTERNAL and legal-implication claims against an official/public source in the same session, per ground-truth.md (do not assert product/feature/legal facts from memory).
- You SHOULD prioritize: legal/compliance claims → product-capability claims → statistics/quotes → general background.
- You MUST mark any claim you could not verify as "Unverified" rather than presenting it as confirmed.

### 5. Produce the Structured Report

Output a single report with a clear verdict.

**Required sections:**
- **Verdict:** SAFE TO PUBLISH / FIX REQUIRED, with the count of must-fix items.
- **Claims table:** claim · location · type · verified? · source.
- **Must-fix list:** each incorrect/unverifiable/leak-risk claim with the specific fix.
- **Leak audit:** every INTERNAL-DERIVED claim and its resolution (cite / reframe / remove).

**Constraints:**
- You MUST NOT report "SAFE TO PUBLISH" if any LEAK RISK or unverified legal-implication claim remains.
- You MUST quote the specific problematic text in each must-fix item so the user can locate it.
- You SHOULD scan for competitor-product and third-party-branding issues too (see pre-publish-safety.md) and fold them into the must-fix list.

## Examples

### Example Output (abbreviated)

```
Verdict: FIX REQUIRED — 3 must-fix (1 leak risk, 2 unverified)

Must-fix:
1. [LEAK RISK] §3 "the retention window is 30 days" — knowable only from an internal
   spike; no public source. → cite public docs, reframe as "in my testing", or remove.
2. [UNVERIFIED] §5 "Service X is GA in eu-central-1" — could not confirm. → verify or hedge.
3. [LEAK RISK] §2 "model Y is available in the EU mantle" — internal-derived. → remove/reframe.
```
