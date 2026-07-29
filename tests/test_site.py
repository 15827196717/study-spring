from pathlib import Path
import re
import unittest

from tools.note_converter.model import Block, Note, Section
from tools.note_converter.site import render_site


SITE_DIR = Path(__file__).parents[1] / "site"


class SiteTests(unittest.TestCase):
    def test_renders_local_semantic_reader_contract(self):
        note = Note(
            "Spring Notes",
            ("1. Question one",),
            (
                Section(
                    "01-one",
                    "One",
                    (
                        Block("paragraph", "1. Question one"),
                        Block("paragraph", "Answer"),
                        Block("image", "https://source.invalid/1"),
                    ),
                ),
            ),
        )
        html = render_site(
            note, {"https://source.invalid/1": "assets/images/note-001.png"}
        )

        for token in (
            "<main",
            "<article",
            "<nav data-toc",
            'id="01-one"',
            'id="q-1-1"',
            "data-search-input",
            "data-search-count",
            "data-theme-toggle",
            "data-toc-toggle",
            "data-progress",
            "data-back-to-top",
            'loading="lazy"',
            "assets/images/note-001.png",
            "styles.css",
            "app.js",
        ):
            self.assertIn(token, html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("cdn", html.lower())

    def test_uses_sequence_to_keep_duplicate_question_numbers_unique(self):
        note = Note(
            "Spring Notes",
            ("1. First", "1. Second"),
            (
                Section(
                    "01-one",
                    "One",
                    (
                        Block("paragraph", "1. First"),
                        Block("paragraph", "1. Second"),
                    ),
                ),
            ),
        )

        html = render_site(note, {})

        self.assertIn('id="q-1-1"', html)
        self.assertIn('id="q-1-2"', html)

    def test_active_toc_contract_covers_hash_scroll_and_page_bottom(self):
        script = (SITE_DIR / "app.js").read_text(encoding="utf-8")

        self.assertIn("function syncActiveHeading(", script)
        self.assertRegex(
            script,
            re.compile(
                r'addEventListener\("hashchange".*?syncActiveHeading',
                re.DOTALL,
            ),
        )
        self.assertRegex(
            script,
            re.compile(
                r'addEventListener\("scroll",\s*\(\)\s*=>\s*\{.*?'
                r"syncActiveHeading\(\)",
                re.DOTALL,
            ),
        )
        self.assertIn("scrollY + innerHeight >= document.documentElement.scrollHeight", script)

    def test_mobile_content_wraps_without_disabling_code_scrolling(self):
        styles = (SITE_DIR / "styles.css").read_text(encoding="utf-8")

        self.assertRegex(styles, r"main\s*\{[^}]*min-width:\s*0")
        self.assertRegex(
            styles,
            r"\.question\s+:where\(p,\s*li\)\s*\{[^}]*overflow-wrap:\s*anywhere",
        )
        self.assertRegex(styles, r"pre\s*\{[^}]*overflow-x:\s*auto")


if __name__ == "__main__":
    unittest.main()
