from pathlib import Path
import unittest

from tools.note_converter.model import Link, Table, TableCell, TableRow
from tools.note_converter.parser import SECTION_FILES, parse_snapshot, question_titles


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_snapshot.txt"
STRUCTURED_FIXTURE = Path(__file__).parent / "fixtures" / "structured_snapshot.txt"


def full_like_snapshot(toc_titles: list[str], body_titles: list[str]) -> str:
    lines = ["- iframe:", "  - generic: title"]
    for number, title in enumerate(toc_titles, start=1):
        lines.extend((f"  - generic: {title}", f"  - generic: {number}. question"))
    for title in body_titles:
        lines.extend((f"  - generic: {title}", "  - generic: answer"))
    lines.append("- paragraph: footer")
    return "\n".join(lines)


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.note = parse_snapshot(FIXTURE.read_text(encoding="utf-8"))

    def test_skips_source_table_of_contents_and_uses_detailed_body(self):
        self.assertEqual("Spring鏈€鏂板叏瀹舵《闈㈣瘯棰?", self.note.title)
        self.assertEqual(
            ["涓€銆丼pring Framework", "浜屻€丼pring IOC"],
            [section.title for section in self.note.sections],
        )
        self.assertEqual(
            ["1.闂涓€", "2.闂浜?"], question_titles(self.note)
        )

    def test_preserves_code_image_and_bullet_blocks(self):
        kinds = [
            block.kind for section in self.note.sections for block in section.blocks
        ]
        self.assertIn("code", kinds)
        self.assertIn("image", kinds)
        self.assertIn("bullet", kinds)

    def test_parses_the_utf8_section_titles_used_by_the_real_snapshot(self):
        snapshot = FIXTURE.read_text(encoding="utf-8")
        replacements = {
            "Spring鏈€鏂板叏瀹舵《闈㈣瘯棰?": "Spring最新全家桶面试题",
            "涓€銆丼pring Framework": "一、Spring Framework",
            "浜屻€丼pring IOC": "二、Spring IOC",
        }
        for old, new in replacements.items():
            snapshot = snapshot.replace(old, new)

        note = parse_snapshot(snapshot)

        self.assertEqual("Spring最新全家桶面试题", note.title)
        self.assertEqual(
            ["一、Spring Framework", "二、Spring IOC"],
            [section.title for section in note.sections],
        )

    def test_preserves_question_titles_with_the_ideographic_comma_numbering(self):
        snapshot = FIXTURE.read_text(encoding="utf-8").replace(
            "1.闂涓€", "1、问题一"
        ).replace("2.闂浜?", "2.问题二")

        note = parse_snapshot(snapshot)

        self.assertEqual(["1、问题一", "2.问题二"], question_titles(note))

    def test_preserves_an_image_block_for_any_quoted_url(self):
        snapshot = FIXTURE.read_text(encoding="utf-8").replace(
            "https://share.note.youdao.com/yws/public/resource/example/1",
            "http://images.example.test/note.png",
        )

        note = parse_snapshot(snapshot)

        images = [
            block.text
            for section in note.sections
            for block in section.blocks
            if block.kind == "image"
        ]
        self.assertEqual(["http://images.example.test/note.png"], images)

    def test_preserves_link_label_and_url_from_the_accessibility_subtree(self):
        note = parse_snapshot(STRUCTURED_FIXTURE.read_text(encoding="utf-8"))

        link_blocks = [
            block
            for section in note.sections
            for block in section.blocks
            if block.kind == "link"
        ]

        self.assertEqual(
            [
                Link(
                    "Spring 版本说明",
                    "https://github.com/spring-projects/spring-framework/releases/tag/v5.2.7.RELEASE",
                )
            ],
            [block.link for block in link_blocks],
        )

    def test_preserves_table_rows_empty_cells_and_multiline_cells(self):
        note = parse_snapshot(STRUCTURED_FIXTURE.read_text(encoding="utf-8"))

        table_blocks = [
            block
            for section in note.sections
            for block in section.blocks
            if block.kind == "table"
        ]

        self.assertEqual(
            Table(
                (
                    TableRow((TableCell(("事务一",)), TableCell(("事务二",)))),
                    TableRow(
                        (
                            TableCell(()),
                            TableCell(("update t_user", "set balance=800")),
                        )
                    ),
                )
            ),
            table_blocks[0].table,
        )

    def test_rejects_duplicate_detailed_sections_in_a_full_snapshot(self):
        titles = [title for title, _ in SECTION_FILES]

        with self.assertRaises(ValueError):
            parse_snapshot(
                full_like_snapshot(titles, [*titles, titles[-1]]),
                require_complete=True,
            )

    def test_rejects_an_incomplete_full_snapshot_with_a_malformed_toc(self):
        titles = [title for title, _ in SECTION_FILES[:-1]]

        with self.assertRaises(ValueError):
            parse_snapshot(
                full_like_snapshot(titles, titles), require_complete=True
            )

    def test_rejects_sparse_toc_with_nine_detailed_sections_when_complete(self):
        titles = [title for title, _ in SECTION_FILES]

        with self.assertRaises(ValueError):
            parse_snapshot(
                full_like_snapshot(titles[:2], titles[:-1]), require_complete=True
            )

    def test_rejects_sparse_toc_with_eleven_detailed_sections_when_complete(self):
        titles = [title for title, _ in SECTION_FILES]

        with self.assertRaises(ValueError):
            parse_snapshot(
                full_like_snapshot(titles[:2], [*titles, titles[-1]]),
                require_complete=True,
            )

    def test_rejects_out_of_order_detailed_sections_when_complete(self):
        titles = [title for title, _ in SECTION_FILES]

        with self.assertRaisesRegex(ValueError, "expected detailed sections"):
            parse_snapshot(
                full_like_snapshot(titles, [titles[1], titles[0], *titles[2:]]),
                require_complete=True,
            )

if __name__ == "__main__":
    unittest.main()
