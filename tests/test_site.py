import unittest

from tools.note_converter.model import Block, Note, Section
from tools.note_converter.site import render_site


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


if __name__ == "__main__":
    unittest.main()
