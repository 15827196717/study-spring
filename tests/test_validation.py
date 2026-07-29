from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from tools.validate_generated import validate


def write_valid_fixture(root: Path) -> None:
    (root / "tools").mkdir()
    (root / "docs").mkdir()
    (root / "assets" / "images").mkdir(parents=True)
    (root / "site").mkdir()
    title = "1.问题一"
    manifest = {
        "section_titles": ["一、One"],
        "chapter_files": ["docs/01-one.md"],
        "question_count": 1,
        "question_titles_sha256": sha256(title.encode()).hexdigest(),
        "image_count": 1,
    }
    (root / "tools" / "content_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    (root / "README.md").write_text(
        "[第一章](docs/01-one.md)", encoding="utf-8"
    )
    (root / "docs" / "01-one.md").write_text(
        "# 一、One\n\n## 1.问题一\n\n"
        "![图片](../assets/images/note-001.png)\n",
        encoding="utf-8",
    )
    (root / "assets" / "images" / "note-001.png").write_bytes(b"png")
    (root / "site" / "index.html").write_text(
        '<img src="assets/images/note-001.png">', encoding="utf-8"
    )


class ValidationTests(unittest.TestCase):
    def test_accepts_complete_local_fixture(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            self.assertEqual([], validate(root))

    def test_reports_missing_chapter_and_image(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "docs" / "01-one.md").unlink()
            (root / "assets" / "images" / "note-001.png").unlink()
            errors = "\n".join(validate(root))
            self.assertIn("docs/01-one.md", errors)
            self.assertIn("expected 1 images", errors)

    def test_reports_broken_relative_markdown_link(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "README.md").write_text(
                "[missing chapter](docs/missing.md#part)", encoding="utf-8"
            )
            self.assertIn("broken link", "\n".join(validate(root)))

    def test_reports_remote_youdao_runtime_reference(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "site" / "index.html").write_text(
                '<img src="https://share.note.youdao.com/image">',
                encoding="utf-8",
            )
            self.assertIn("forbidden URL", "\n".join(validate(root)))

    def test_reports_question_manifest_mismatch(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            chapter = root / "docs" / "01-one.md"
            chapter.write_text("# 一、One\n\n## 2.不同问题\n", encoding="utf-8")
            self.assertIn("question title hash", "\n".join(validate(root)))


if __name__ == "__main__":
    unittest.main()
