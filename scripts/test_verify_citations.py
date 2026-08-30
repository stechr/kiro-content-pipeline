#!/usr/bin/env python3
"""Tests for verify_citations.py and ai_attribution.py.

Run:  python3 -m pytest test_verify_citations.py -q
or:   python3 test_verify_citations.py   (falls back to a tiny runner)

External URL resolution is NOT exercised here (offline-safe); all scans use the
do_external=False path so the suite is hermetic.
"""
from __future__ import annotations

import importlib.util
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    # register before exec so @dataclass introspection (py3.12+) can resolve the module
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


vc = _load("verify_citations")
attr = _load("ai_attribution")


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

CLEAN = """---
title: t
---
# Post

AWS announced cross-account access for the MCP Server [1]. It builds on an
earlier post of mine [2].

## Sources

[1] AWS, "What's New" — https://aws.amazon.com/about-aws/whats-new/x/
[2] Stefan Christoph, "Earlier" — [/blog/earlier/](/blog/earlier/)
"""

LIST_SOURCES = """# Post
A claim [1]. Another [2].

## Sources

- [1] Amazon Bedrock AgentCore — [aws.amazon.com](https://aws.amazon.com/bedrock/agentcore/)
- [2] Kiro — [kiro.dev](https://kiro.dev)
"""

UNDEFINED = """# Post
A claim with a dangling citation [7].

## Sources

[1] Only one — https://example.com/
"""

NO_SOURCES = """# Post
A claim [1] with no Sources section at all.
"""

UNCITED = """# Post
The service now supports up to 10,000 requests per second.
I think this is a good direction, in my experience.

## Sources
[1] x — https://example.com/
"""

COLON_CITE = """# Post
They map onto the layers below [2]:

- a
- b

## Sources
[1] a — https://example.com/a
[2] b — https://example.com/b
"""


def _scan(text):
    return vc.scan_text(text, do_external=False, do_fetch=False)


def _hard(rep):
    return [e for e in rep.existence
            if e.kind in ("undefined-citation", "broken-source", "no-url")]


# --------------------------------------------------------------------------- #
# existence
# --------------------------------------------------------------------------- #

def test_clean_no_hard_failures():
    rep = _scan(CLEAN)
    assert _hard(rep) == []
    assert rep.stats["sources_defined"] == 2


def test_relative_internal_url_is_not_no_url():
    rep = _scan(CLEAN)
    # [2] uses a relative /blog/earlier/ — must NOT be flagged no-url
    assert not any(e.kind == "no-url" for e in rep.existence)


def test_list_bullet_sources_parsed():
    rep = _scan(LIST_SOURCES)
    assert rep.stats["sources_defined"] == 2
    assert _hard(rep) == []


def test_undefined_citation_detected():
    rep = _scan(UNDEFINED)
    kinds = [e.kind for e in rep.existence]
    assert "undefined-citation" in kinds          # [7] has no source
    assert "orphan-source" in kinds               # [1] never cited


def test_no_sources_section_all_undefined():
    rep = _scan(NO_SOURCES)
    assert any(e.kind == "undefined-citation" for e in _hard(rep))


def test_colon_after_citation_is_still_a_citation():
    # "[2]:" in the body is a citation, not a ref definition -> [2] not orphan
    rep = _scan(COLON_CITE)
    assert not any(e.kind == "orphan-source" and e.ref == "[2]" for e in rep.existence)
    assert _hard(rep) == []


# --------------------------------------------------------------------------- #
# support worklist
# --------------------------------------------------------------------------- #

def test_support_worklist_built():
    rep = _scan(CLEAN)
    assert len(rep.support) == 2
    assert all(i.support == "NEEDS_LLM_JUDGMENT" for i in rep.support)
    # claim text carries the citation's sentence
    assert any("cross-account" in i.claim for i in rep.support)


# --------------------------------------------------------------------------- #
# uncited heuristic
# --------------------------------------------------------------------------- #

def test_uncited_factual_claim_flagged():
    rep = _scan(UNCITED)
    assert any("10,000" in u.sentence or "supports" in u.reason for u in rep.uncited)


def test_first_person_opinion_not_flagged():
    rep = _scan(UNCITED)
    assert not any("good direction" in u.sentence for u in rep.uncited)


# --------------------------------------------------------------------------- #
# attribution helper
# --------------------------------------------------------------------------- #

def test_attribution_absent():
    assert attr.check_text("# Post\njust prose.")["present"] is False


def test_attribution_present_prose():
    res = attr.check_text("# Post\n\n*Written with AI assistance, human-reviewed.*")
    assert res["present"] is True


def test_attribution_present_frontmatter():
    res = attr.check_text("---\nai_assistance: true\n---\n# Post")
    assert res["present"] is True


def test_emit_styles_exist():
    for style in ("footer", "inline", "frontmatter"):
        assert style in attr.STATEMENTS and attr.STATEMENTS[style].strip()


# --------------------------------------------------------------------------- #
# tiny fallback runner
# --------------------------------------------------------------------------- #

if __name__ == "__main__":
    import sys
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ok  {fn.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"FAIL  {fn.__name__}: {exc}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
