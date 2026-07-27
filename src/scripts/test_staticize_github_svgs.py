#!/usr/bin/env python3
"""Unit tests for staticize_github_svgs.py.

Runs entirely offline against inline SVG fixtures that mimic the two real
card sources this script processes:

  - github-readme-stats cards (stats.svg / top-langs.svg), which emit
    double-quoted XML attributes and put their animation CSS in a <style>
    block;
  - streak-stats.demolab.com (streak.svg), which emits SINGLE-quoted XML
    attributes and puts its animation CSS in inline style='...' attributes.

The single-quoted form is the one that corrupted the committed streak.svg
on 2026-07-21: the animation-stripping character classes excluded '"' but
not "'", so a match starting inside style='...' ate straight through the
closing quote and the following markup until the next ';', '"', or '}',
truncating the file into invalid XML.

Invoke with: python -m unittest src.scripts.test_staticize_github_svgs -v
"""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
import xml.dom.minidom
from pathlib import Path

from src.scripts import staticize_github_svgs as staticize_mod
from src.scripts.staticize_github_svgs import staticize, staticize_file

# Trimmed replica of a real streak-stats.demolab.com card: single-quoted
# attributes, @keyframes in a <style> block, and per-node inline
# style='opacity: 0; animation: ...' declarations (note the space after
# each ':', exactly as the service emits them).
STREAK_STATS_STYLE_SVG = """<svg xmlns='http://www.w3.org/2000/svg' xmlns:xlink='http://www.w3.org/1999/xlink'
                style='isolation: isolate' viewBox='0 0 495 195' width='495px' height='195px' direction='ltr'>
        <style>
            @keyframes currstreak {
                0% { font-size: 3px; opacity: 0.2; }
                80% { font-size: 34px; opacity: 1; }
                100% { font-size: 28px; opacity: 1; }
            }
            @keyframes fadein {
                0% { opacity: 0; }
                100% { opacity: 1; }
            }
        </style>
        <g clip-path='url(#outer_rectangle)'>
            <g style='isolation: isolate'>
                <rect stroke='#000000' stroke-opacity='0' fill='#0b0f14' rx='4.5' x='0.5' y='0.5' width='494' height='194'/>
            </g>
            <g transform='translate(82.5, 48)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle' fill='#ffffff' stroke='none' font-weight='700' font-size='28px' font-style='normal' style='opacity: 0; animation: fadein 0.5s linear forwards 0.6s'>
                    5,686
                </text>
            </g>
            <g transform='translate(82.5, 84)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle' fill='#a78bfa' stroke='none' font-weight='400' font-size='14px' font-style='normal' style='opacity: 0; animation: fadein 0.5s linear forwards 0.7s'>
                    Total Contributions
                </text>
            </g>
            <g transform='translate(247.5, 48)'>
                <text x='0' y='32' stroke-width='0' text-anchor='middle' fill='#ffffff' stroke='none' font-weight='700' font-size='28px' font-style='normal' style='animation: currstreak 0.6s linear forwards'>
                    1
                </text>
            </g>
        </g>
    </svg>
"""

# Double-quoted github-readme-stats style content: the pre-existing case
# that already worked and must keep working.
README_STATS_STYLE_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="450" height="195" viewBox="0 0 450 195">
  <style>
    .stat { font: 600 14px sans-serif; fill: #E5E7EB; }
    .stagger { opacity:0; animation: fadeInAnimation 0.3s ease-in-out forwards; }
    @keyframes fadeInAnimation {
      from { opacity: 0; }
      to { opacity: 1; }
    }
  </style>
  <text class="stat" x="25" y="50" style="animation-delay: 450ms">Total Stars Earned: 42</text>
</svg>
"""


def parses(svg_text: str) -> bool:
    try:
        xml.dom.minidom.parseString(svg_text)
    except Exception:
        return False
    return True


class SingleQuotedAttributeTests(unittest.TestCase):
    """The 2026-07-21 streak.svg corruption: staticize() must never eat
    across a single-quoted attribute boundary."""

    def test_result_is_well_formed_xml(self) -> None:
        result = staticize(STREAK_STATS_STYLE_SVG)
        self.assertTrue(
            parses(result),
            "staticize() of a single-quoted-attribute (streak-stats style) SVG "
            "must stay well-formed XML",
        )

    def test_content_outside_animation_declarations_is_untouched(self) -> None:
        result = staticize(STREAK_STATS_STYLE_SVG)
        # Visible card text survives.
        self.assertIn("5,686", result)
        self.assertIn("Total Contributions", result)
        self.assertIn(">\n                    1\n                </text>", result)
        # Attributes that follow a staticized style='...' attribute survive.
        self.assertIn("fill='#ffffff'", result)
        self.assertIn("fill='#a78bfa'", result)
        self.assertIn("font-size='28px'", result)
        # Non-animation style attributes are left alone.
        self.assertIn("style='isolation: isolate'", result)
        # The document still closes properly.
        self.assertIn("</svg>", result)

    def test_animation_and_keyframes_are_fully_removed(self) -> None:
        result = staticize(STREAK_STATS_STYLE_SVG)
        self.assertNotIn("animation", result)
        self.assertNotIn("@keyframes", result)

    def test_hidden_by_default_nodes_become_visible(self) -> None:
        # streak-stats writes 'opacity: 0;' (with a space) on every node it
        # then fades in; once animations are stripped those nodes must not
        # stay invisible.
        result = staticize(STREAK_STATS_STYLE_SVG)
        self.assertNotIn("opacity: 0;", result)
        self.assertNotIn("opacity:0", result)
        # XML attribute opacity (not a CSS declaration) is untouched.
        self.assertIn("stroke-opacity='0'", result)


class DoubleQuotedAttributeTests(unittest.TestCase):
    """Regression cover for the github-readme-stats cards that already
    staticized correctly before the single-quote fix."""

    def test_result_is_well_formed_and_static(self) -> None:
        result = staticize(README_STATS_STYLE_SVG)
        self.assertTrue(parses(result))
        self.assertNotIn("animation", result)
        self.assertNotIn("@keyframes", result)
        self.assertNotIn("opacity:0", result)

    def test_content_outside_animation_declarations_is_untouched(self) -> None:
        result = staticize(README_STATS_STYLE_SVG)
        self.assertIn("Total Stars Earned: 42", result)
        self.assertIn('.stat { font: 600 14px sans-serif; fill: #E5E7EB; }', result)


class OpacityPrecisionTests(unittest.TestCase):
    def test_nonzero_opacity_values_are_not_mangled(self) -> None:
        svg = "<svg xmlns='http://www.w3.org/2000/svg'><g style='opacity: 0.85'><text>kept</text></g></svg>"
        result = staticize(svg)
        self.assertIn("opacity: 0.85", result)
        self.assertTrue(parses(result))


class StaticizeFileGuardTests(unittest.TestCase):
    """Belt-and-braces guard: staticize_file() must never write a result
    that fails to parse as XML - it keeps the original file instead."""

    def setUp(self) -> None:
        self._tmp_ctx = tempfile.TemporaryDirectory()
        self.work_dir = Path(self._tmp_ctx.name)

    def tearDown(self) -> None:
        self._tmp_ctx.cleanup()

    def _write(self, name: str, content: str) -> Path:
        path = self.work_dir / name
        path.write_text(content, encoding="utf-8")
        return path

    def test_valid_result_is_written(self) -> None:
        path = self._write("streak.svg", STREAK_STATS_STYLE_SVG)
        wrote = staticize_file(path)
        self.assertTrue(wrote)
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text, staticize(STREAK_STATS_STYLE_SVG))
        self.assertTrue(parses(text))

    def test_invalid_result_leaves_original_untouched_and_warns(self) -> None:
        # Regex staticizing is not XML-aware, so pathological (but
        # well-formed) input can still produce a broken result: here the
        # text node's 'animation:' declaration-lookalike makes the regex
        # eat the opening <tspan> tag but not its closing tag.
        hostile = (
            "<svg xmlns='http://www.w3.org/2000/svg'>"
            "<text>animation: is neat <tspan>really;</tspan></text>"
            "</svg>"
        )
        self.assertTrue(parses(hostile))
        self.assertFalse(
            parses(staticize(hostile)),
            "precondition: this fixture must make bare staticize() emit "
            "broken XML, so the file-level guard has something to catch",
        )

        path = self._write("streak.svg", hostile)
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            wrote = staticize_file(path)

        self.assertFalse(wrote)
        self.assertEqual(path.read_text(encoding="utf-8"), hostile)
        self.assertIn("::warning::", captured.getvalue())

    def test_main_processes_all_svg_files_in_place(self) -> None:
        original_dir = staticize_mod.SVG_DIR
        staticize_mod.SVG_DIR = self.work_dir
        try:
            for name in staticize_mod.SVG_FILES:
                self._write(name, STREAK_STATS_STYLE_SVG)
            staticize_mod.main()
            for name in staticize_mod.SVG_FILES:
                with self.subTest(file=name):
                    text = (self.work_dir / name).read_text(encoding="utf-8")
                    self.assertTrue(parses(text))
                    self.assertNotIn("animation", text)
        finally:
            staticize_mod.SVG_DIR = original_dir


if __name__ == "__main__":
    unittest.main()
