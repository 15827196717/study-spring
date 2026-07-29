import unittest

from tools.note_converter.markdown import render_chapters, render_readme
from tools.note_converter.model import (
    Block,
    Link,
    Note,
    Section,
    Table,
    TableCell,
    TableRow,
)


NOTE = Note(
    "Spring Notes",
    ("1.问题一", "2.问题二"),
    (
        Section(
            "01-one",
            "一、One",
            (
                Block("paragraph", "1.问题一"),
                Block("paragraph", "答案"),
                Block("bullet", "要点"),
                Block("code", "class Demo {}"),
                Block("image", "https://source.invalid/1"),
            ),
        ),
        Section(
            "02-two",
            "二、Two",
            (Block("paragraph", "2.问题二"),),
        ),
    ),
)


class MarkdownTests(unittest.TestCase):
    def test_renders_questions_blocks_images_and_navigation(self):
        chapters = render_chapters(
            NOTE, {"https://source.invalid/1": "assets/images/note-001.png"}
        )

        first = chapters["docs/01-one.md"]
        self.assertIn("## 1.问题一", first)
        self.assertIn("- 要点", first)
        self.assertIn("```\nclass Demo {}\n```", first)
        self.assertIn(
            "![笔记图片 1：1.问题一](../assets/images/note-001.png)", first
        )
        self.assertIn("[返回首页](../README.md)", first)
        self.assertIn("[下一章](02-two.md)", first)

    def test_renders_repository_entry_points(self):
        readme = render_readme(NOTE)

        self.assertIn("docs/01-one.md", readme)
        self.assertIn("二、框架源码专题", readme)
        self.assertIn("最新Spring全家桶面试题—图灵徐庶.docx", readme)
        self.assertIn("https://15827196717.github.io/study-spring/", readme)

    def test_last_chapter_footer_has_no_trailing_separator(self):
        chapters = render_chapters(
            NOTE, {"https://source.invalid/1": "assets/images/note-001.png"}
        )

        self.assertEqual(
            "[上一章](01-one.md) · [返回首页](../README.md)",
            chapters["docs/02-two.md"].splitlines()[-1],
        )

    def test_keeps_numbered_answer_paragraphs_out_of_question_headings(self):
        note = Note(
            "Spring Notes",
            ("1. Canonical question",),
            (
                Section(
                    "01-one",
                    "One",
                    (
                        Block("paragraph", "1. Canonical question"),
                        Block("paragraph", "1. Numbered answer step"),
                    ),
                ),
            ),
        )

        chapter = render_chapters(note, {})["docs/01-one.md"]

        self.assertIn("## 1. Canonical question", chapter)
        self.assertNotIn("## 1. Numbered answer step", chapter)
        self.assertIn("1. Numbered answer step\n", chapter)

    def test_renders_links_tables_and_literal_xml_as_github_markdown(self):
        note = Note(
            "Spring Notes",
            ("1.问题一",),
            (
                Section(
                    "01-one",
                    "一、One",
                    (
                        Block("paragraph", "1.问题一"),
                        Block("paragraph", "XML：<bean> & <context>"),
                        Block("bullet", "条件：a < b & b > 0"),
                        Block(
                            "link",
                            link=Link(
                                "Spring [版本]",
                                "https://github.com/spring-projects/spring-framework",
                            ),
                        ),
                        Block(
                            "table",
                            table=Table(
                                (
                                    TableRow(
                                        (
                                            TableCell(("模式",)),
                                            TableCell(("说明",)),
                                        )
                                    ),
                                    TableRow(
                                        (
                                            TableCell(()),
                                            TableCell(("第一行", "第二行 | 详情")),
                                        )
                                    ),
                                )
                            ),
                        ),
                    ),
                ),
            ),
        )

        chapter = render_chapters(note, {})["docs/01-one.md"]

        self.assertIn("XML：&lt;bean&gt; &amp; &lt;context&gt;", chapter)
        self.assertIn("- 条件：a &lt; b &amp; b &gt; 0", chapter)
        self.assertIn(
            r"[Spring \[版本\]](https://github.com/spring-projects/spring-framework)",
            chapter,
        )
        self.assertIn("| 模式 | 说明 |", chapter)
        self.assertIn("| --- | --- |", chapter)
        self.assertIn(r"|  | 第一行<br>第二行 \| 详情 |", chapter)

    def test_image_alt_includes_sequence_and_current_question_context(self):
        chapter = render_chapters(
            NOTE, {"https://source.invalid/1": "assets/images/note-001.png"}
        )["docs/01-one.md"]

        self.assertIn(
            "![笔记图片 1：1.问题一](../assets/images/note-001.png)", chapter
        )


if __name__ == "__main__":
    unittest.main()
