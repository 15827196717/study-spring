from pathlib import Path
import re
import subprocess
import unittest

from tools.note_converter.model import (
    Block,
    Link,
    Note,
    Section,
    Table,
    TableCell,
    TableRow,
)
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

    def test_renders_content_links_semantic_tables_and_literal_xml(self):
        note = Note(
            "Spring Notes",
            ("1. Question one",),
            (
                Section(
                    "01-one",
                    "One",
                    (
                        Block("paragraph", "1. Question one"),
                        Block("paragraph", "XML: <bean> & <context>"),
                        Block(
                            "link",
                            link=Link(
                                "Spring releases",
                                "https://github.com/spring-projects/spring-framework/releases",
                            ),
                        ),
                        Block(
                            "table",
                            table=Table(
                                (
                                    TableRow(
                                        (TableCell(("事务一",)), TableCell(("事务二",)))
                                    ),
                                    TableRow(
                                        (
                                            TableCell(()),
                                            TableCell(("update t_user", "commit")),
                                        )
                                    ),
                                )
                            ),
                        ),
                        Block("image", "https://source.invalid/1"),
                    ),
                ),
            ),
        )

        html = render_site(
            note, {"https://source.invalid/1": "assets/images/note-001.png"}
        )

        self.assertIn("<p>XML: &lt;bean&gt; &amp; &lt;context&gt;</p>", html)
        self.assertIn(
            '<a href="https://github.com/spring-projects/spring-framework/releases">'
            "Spring releases</a>",
            html,
        )
        self.assertIn("<table><thead><tr><th>事务一</th><th>事务二</th>", html)
        self.assertIn("<tbody><tr><td></td><td>update t_user<br>commit</td>", html)
        self.assertIn('alt="笔记图片 1：1. Question one"', html)

    def test_keeps_a_bullet_link_inside_a_semantic_list(self):
        note = Note(
            "Spring Notes",
            (),
            (
                Section(
                    "01-one",
                    "One",
                    (
                        Block(
                            "link",
                            link=Link("@AspectJ", "https://github.com/AspectJ"),
                            is_bullet=True,
                        ),
                    ),
                ),
            ),
        )

        html = render_site(note, {})

        self.assertIn(
            '<ul><li><a href="https://github.com/AspectJ">@AspectJ</a></li></ul>',
            html,
        )

    def test_wraps_wide_table_in_keyboard_accessible_scroll_region(self):
        headers = ("Propagation", "External transaction", "Internal action", "Usage")
        values = (
            "REQUIRES_NEW_WITH_A_LONG_UNBROKEN_NAME",
            "SuspendTheExistingTransactionBeforeContinuing",
            "CreateAnIndependentTransactionForTheNestedCall",
            "TransactionalPropagationRequiresNew",
        )
        note = Note(
            "Spring Notes",
            (),
            (
                Section(
                    "01-one",
                    "One",
                    (
                        Block(
                            "table",
                            table=Table(
                                (
                                    TableRow(
                                        tuple(TableCell((value,)) for value in headers)
                                    ),
                                    TableRow(
                                        tuple(TableCell((value,)) for value in values)
                                    ),
                                )
                            ),
                        ),
                    ),
                ),
            ),
        )

        html = render_site(note, {})
        styles = (SITE_DIR / "styles.css").read_text(encoding="utf-8")

        self.assertIn(
            '<div class="table-scroll" role="region" '
            'aria-label="Scrollable data table" tabindex="0"><table>',
            html,
        )
        self.assertIn("</table></div>", html)
        self.assertEqual(4, html.count("<th>"))
        self.assertEqual(4, html.count("<td>"))
        self.assertRegex(
            styles,
            r"\.table-scroll\s*\{[^}]*max-width:\s*100%;"
            r"[^}]*overflow-x:\s*auto",
        )
        self.assertRegex(
            styles,
            r"\.table-scroll table\s*\{[^}]*min-width:\s*",
        )

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

    def test_search_updates_toc_and_progress_using_only_visible_headings(self):
        result = subprocess.run(
            ["node", str(Path(__file__).with_name("site_search_behavior.js"))],
            cwd=SITE_DIR.parent,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
