#!/usr/bin/env python3
"""
test_ai_smell_scan.py — stdlib unittest regression suite for ai_smell_scan.py.

Run:  python3 -m unittest test_ai_smell_scan -v
  or: python3 test_ai_smell_scan.py

No third-party deps. Imports the scanner module by file path so it works
regardless of the current working directory.
"""
import importlib.util
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location(
    "ai_smell_scan", os.path.join(_HERE, "ai_smell_scan.py"))
mod = importlib.util.module_from_spec(_spec)
# register before exec so @dataclass introspection (py3.12+) can resolve the module
sys.modules["ai_smell_scan"] = mod
_spec.loader.exec_module(mod)


def cats(rep, tier):
    return [f.category for f in rep.by_tier(tier)]


class ArtifactTier(unittest.TestCase):
    def test_chatgpt_utm_is_artifact(self):
        rep = mod.scan_text("See https://x.com/a?utm_source=chatgpt.com here.")
        self.assertIn("utm-source-ai", cats(rep, mod.ARTIFACT))

    def test_openai_utm_is_artifact(self):
        rep = mod.scan_text("ref?utm_source=openai")
        self.assertIn("utm-source-ai", cats(rep, mod.ARTIFACT))

    def test_turn_search_token(self):
        rep = mod.scan_text("as shown turn0search3 in the data")
        self.assertIn("turn-search", cats(rep, mod.ARTIFACT))

    def test_oaicite_markup(self):
        rep = mod.scan_text("text :contentReference[oaicite:2]{index=2} more")
        self.assertIn("oaicite", cats(rep, mod.ARTIFACT))

    def test_citation_glyph(self):
        rep = mod.scan_text("source 【85†L261-269】 end")
        self.assertIn("citation-glyph", cats(rep, mod.ARTIFACT))

    def test_placeholder_date(self):
        rep = mod.scan_text("date: 2026-XX-XX")
        self.assertIn("placeholder-date", cats(rep, mod.ARTIFACT))

    def test_bracket_placeholder(self):
        rep = mod.scan_text("Regards, [Your Name]")
        self.assertIn("bracket-placeholder", cats(rep, mod.ARTIFACT))

    def test_artifact_inside_code_block_is_ignored(self):
        # artifacts in fenced code must NOT be flagged (it's documentation)
        txt = "```\ncurl 'x?utm_source=chatgpt.com'\n```\nClean prose."
        rep = mod.scan_text(txt)
        self.assertEqual(rep.by_tier(mod.ARTIFACT), [])

    def test_bare_footnote_marker_not_flagged(self):
        rep = mod.scan_text("This is a fact [3] with a citation.")
        self.assertEqual(rep.by_tier(mod.ARTIFACT), [])


class SignalTier(unittest.TestCase):
    def test_negative_parallelism_not_just(self):
        rep = mod.scan_text("This is not just a tool, but a platform.")
        self.assertIn("negative-parallelism", cats(rep, mod.SIGNAL))

    def test_negative_parallelism_its_not(self):
        rep = mod.scan_text("It's not about speed, it's about safety.")
        self.assertIn("negative-parallelism", cats(rep, mod.SIGNAL))

    def test_copula_avoidance(self):
        rep = mod.scan_text("The agent serves as a coordinator.")
        self.assertIn("copula-avoidance", cats(rep, mod.SIGNAL))

    def test_challenges_future_heading(self):
        rep = mod.scan_text("# Title\n\n## Challenges and Future Prospects\n\nText.")
        self.assertIn("challenges-future-outline", cats(rep, mod.SIGNAL))

    def test_despite_formula(self):
        rep = mod.scan_text("Despite its promise, the tool faces challenges ahead.")
        self.assertIn("challenges-future-outline", cats(rep, mod.SIGNAL))

    def test_bold_sentence_header(self):
        rep = mod.scan_text("**Key point.** This is the body text after it.")
        self.assertIn("bold-sentence-header", cats(rep, mod.SIGNAL))

    def test_ai_vocabulary(self):
        rep = mod.scan_text("We delve into the comprehensive landscape.")
        self.assertIn("ai-vocabulary", cats(rep, mod.SIGNAL))

    def test_emdash_excessive_hard_fail(self):
        # dense em-dashes -> very high rate -> hard-fail 'em-dash-excessive'
        rep = mod.scan_text("a — " * 12 + "end of the line here.")
        self.assertIn("em-dash-excessive", cats(rep, mod.SIGNAL))

    def test_emdash_overuse_advisory_low_rate(self):
        # >10 em-dashes but spread over many words -> rate <= hard threshold ->
        # advisory 'em-dash-overuse', NOT the hard-fail category
        text = ("word " * 60 + "— ") * 11 + "tail words here to finish the prose."
        sig = cats(mod.scan_text(text), mod.SIGNAL)
        self.assertIn("em-dash-overuse", sig)
        self.assertNotIn("em-dash-excessive", sig)

    def test_strong_vocab_hard_fail(self):
        rep = mod.scan_text("We delve into the tapestry of ideas here today.")
        self.assertIn("ai-vocabulary-strong", cats(rep, mod.SIGNAL))

    def test_soft_vocab_single_is_advisory(self):
        # a single common word -> advisory 'ai-vocabulary', not hard-fail
        sig = cats(mod.scan_text("We leverage the platform to ship faster now."), mod.SIGNAL)
        self.assertIn("ai-vocabulary", sig)
        self.assertNotIn("ai-vocabulary-overused", sig)

    def test_soft_vocab_repeat_hard_fail(self):
        rep = mod.scan_text("We leverage this. We leverage that. We leverage more.")
        self.assertIn("ai-vocabulary-overused", cats(rep, mod.SIGNAL))

    def test_emdash_under_threshold_not_flagged(self):
        rep = mod.scan_text("a — b — c, normal prose with a few dashes.")
        self.assertNotIn("em-dash-overuse", cats(rep, mod.SIGNAL))


class StyleTier(unittest.TestCase):
    def test_curly_quotes_are_style_not_signal(self):
        rep = mod.scan_text("He said \u201chello\u201d and it\u2019s fine.")
        self.assertIn("curly-quotes", cats(rep, mod.STYLE))
        # must never be an artifact or hard signal
        self.assertNotIn("curly-quotes", cats(rep, mod.ARTIFACT))

    def test_title_case_heading_is_style(self):
        rep = mod.scan_text("## Where the Real Gains Are\n\nBody.")
        self.assertIn("title-case-heading", cats(rep, mod.STYLE))

    def test_sentence_case_heading_not_flagged(self):
        # only the first word + proper noun capitalized -> not Title Case
        rep = mod.scan_text("## Why this matters for AWS\n\nBody.")
        self.assertNotIn("title-case-heading", cats(rep, mod.STYLE))

    def test_proper_noun_heading_not_flagged(self):
        rep = mod.scan_text("## Amazon Bedrock AgentCore Runtime\n\nBody.")
        self.assertNotIn("title-case-heading", cats(rep, mod.STYLE))

    def test_skipped_heading_level(self):
        rep = mod.scan_text("## Section\n\n#### Sub\n\nBody.")
        self.assertIn("skipped-heading-level", cats(rep, mod.STYLE))


class Stripping(unittest.TestCase):
    def test_sources_section_excluded_from_vocab(self):
        # 'leverage' only in Sources should not be a SIGNAL
        txt = "Clean body.\n\n## Sources\n\n- We leverage the comprehensive API."
        rep = mod.scan_text(txt)
        self.assertNotIn("ai-vocabulary", cats(rep, mod.SIGNAL))

    def test_emdash_in_code_and_sources_excluded(self):
        txt = "Prose with one — dash.\n\n```\n— — — — — — — — — — — —\n```\n"
        rep = mod.scan_text(txt)
        self.assertEqual(rep.stats["em_dashes"], 1)

    def test_frontmatter_excluded_from_prose_but_artifact_still_caught(self):
        txt = "---\ntitle: My Post\ndate: 2026-XX-XX\n---\n\nClean body here."
        rep = mod.scan_text(txt)
        # placeholder date in frontmatter is still an ARTIFACT (scanned on full doc)
        self.assertIn("placeholder-date", cats(rep, mod.ARTIFACT))


class CommentMode(unittest.TestCase):
    def test_comment_mode_skips_headings(self):
        rep = mod.scan_text("## Title Case Heading Here\n\nBody.", comment_mode=True)
        self.assertNotIn("title-case-heading", cats(rep, mod.STYLE))



class SummaryFrame(unittest.TestCase):
    """'The argument was that X' states X at arm's length instead of asserting it."""

    def test_the_argument_was_that(self):
        rep = mod.scan_text("The argument was that the clip matters more than the model.")
        self.assertIn("summary-frame", cats(rep, mod.SIGNAL))

    def test_the_point_is_that(self):
        rep = mod.scan_text("The point is that nobody measures the input.")
        self.assertIn("summary-frame", cats(rep, mod.SIGNAL))

    def test_what_i_found_was_that(self):
        rep = mod.scan_text("What I found was that the gate could not see it.")
        self.assertIn("summary-frame", cats(rep, mod.SIGNAL))

    def test_the_key_insight_was_that(self):
        rep = mod.scan_text("The key insight was that a label without a gate is useless.")
        self.assertIn("summary-frame", cats(rep, mod.SIGNAL))

    def test_takeaway_was_this(self):
        rep = mod.scan_text("The takeaway was this: measure your metric first.")
        self.assertIn("summary-frame", cats(rep, mod.SIGNAL))

    # --- guards: referring to an argument as an object is legitimate prose ---

    def test_argument_that_x_is_wrong_not_flagged(self):
        rep = mod.scan_text("The argument that codec frames are few-shot examples is wrong.")
        self.assertNotIn("summary-frame", cats(rep, mod.SIGNAL))

    def test_reported_speech_not_flagged(self):
        rep = mod.scan_text("I could not tell what the argument was.")
        self.assertNotIn("summary-frame", cats(rep, mod.SIGNAL))

    def test_the_point_of_not_flagged(self):
        rep = mod.scan_text("The point of the exercise is measurement.")
        self.assertNotIn("summary-frame", cats(rep, mod.SIGNAL))

    def test_possessive_thesis_not_flagged(self):
        rep = mod.scan_text("Their thesis is well known and widely cited.")
        self.assertNotIn("summary-frame", cats(rep, mod.SIGNAL))


if __name__ == "__main__":
    unittest.main(verbosity=2)
