# Pre-Publish Safety

A mandatory gate before any draft is shared or published. Distinct from factual verification (see `ground-truth.md`) — this catches **secrets, PII, and knowledge that should not leave your organization**.

## When this applies

Before sharing or publishing any artifact produced by the pipeline (post, teaser, export), and before committing content to any shared/public repo.

## 1. Secrets & credentials

Scan for and remove:
- API keys, access keys, secret keys, bearer tokens, session IDs
- Private keys / certificates
- `.env` values with real secrets (placeholders like `.env.example` are fine)

## 2. PII & personal paths

- Personal filesystem paths (`/Users/<name>/…`, `/home/<name>/…`) → replace with placeholders or env vars
- Personal identifiers (logins/aliases, private emails) that shouldn't be public — aliases are PII even in comments/tests

## 3. Internal-only references (knowledge leak)

If you work inside an organization, scan for internal-only markers that must not appear in public content:
- Internal email addresses, internal chat/wiki/tool URLs, internal hostnames
- Internal ticket/service identifiers, cloud account IDs, deployed resource IDs (distribution/API/ARNs)

The pipeline's leak scanner automates this. It always applies built-in org-neutral patterns (personal paths, cloud account IDs); add your organization's own markers by copying `config/leak-patterns.sample.json` to `config/leak-patterns.local.json` (gitignored). Aliases come from `pipeline.local.json` → `user_aliases`:

```bash
python3 scripts/leak_scan.py <draft>/post.md --aliases "$(python3 scripts/content_paths.py aliases)"
```

Any finding **blocks** publish until fixed. Public references (official docs, public product names) are not flagged.

## 4. Sanitize at write time, not just scan time

When a script or step generates output that embeds runtime values (account IDs, resource IDs, personal paths), emit **placeholders** (`<ACCOUNT_ID>`, `<RESOURCE_ID>`) or read from env at write time. The pre-publish scan is a backstop, not the primary control.

## 5. Knowledge-leak & claim-type audit

For every material claim about product behavior, capabilities, or legal/compliance implications, classify it:

| Type | Meaning | Action |
|------|---------|--------|
| **EXTERNAL / public** | Has (or can have) a public citation | Verify + cite |
| **FIRST-PARTY** | "In my testing…" framing | OK if true |
| **INTERNAL-DERIVED** | Knowable only from internal/private sources but stated as universal fact | **LEAK RISK** |
| **OPINION** | Clearly framed as opinion | OK |

An INTERNAL-DERIVED claim stated as fact with no public source is a **leak risk**: re-ground it to a public source, soften it to "in my testing", or remove it. Give **legal-implication claims** (data retention, residency, who-can-access, compliance) extra scrutiny — verify each precisely against a public source.

This audit is run and persisted by `post-creation` Step 11d (`claim-verification.md`) and by the standalone `fact-check` skill.

## 6. Verification honesty: "Verified" requires a quoted excerpt

Any `Verified` / `SUPPORTED` verdict recorded in a gate artifact (`claim-verification.md`, a
fact-check report, an independent-model critique) MUST carry a verbatim short quote from the
fetched source that supports the claim.

- A verdict without a quote is treated as **Unverified** by every downstream gate.
- The rule exists because quoting forces the verifier to read the actual supporting sentence
  instead of pattern-matching the page title — the failure mode where two separate gates both
  record "Verified" for a claim the cited page actually contradicts.
