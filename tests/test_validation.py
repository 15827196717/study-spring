from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from tools.validate_generated import validate


def write_valid_fixture(root: Path) -> None:
    (root / "tools").mkdir()
    (root / "docs").mkdir()
    (root / "assets" / "images").mkdir(parents=True)
    (root / "site").mkdir()
    title = "1.问题一"
    (root / "README.md").write_text(
        "[第一章](docs/01-one.md)", encoding="utf-8"
    )
    (root / "docs" / "01-one.md").write_text(
        "# 一、One\n\n## 1.问题一\n\n"
        "![图片](../assets/images/note-001.png)\n",
        encoding="utf-8",
    )
    Image.new("RGB", (2, 2), "red").save(
        root / "assets" / "images" / "note-001.png"
    )
    (root / "site" / "styles.css").write_text("body {}\n", encoding="utf-8")
    (root / "site" / "app.js").write_text("const ready = true;\n", encoding="utf-8")
    (root / "site" / "index.html").write_text(
        '<link rel="stylesheet" href="styles.css">'
        '<a href="https://github.com/example/project">documentation</a>'
        '<img src="assets/images/note-001.png">'
        '<script src="app.js"></script>',
        encoding="utf-8",
    )
    chapter = root / "docs" / "01-one.md"
    site_index = root / "site" / "index.html"
    image = root / "assets" / "images" / "note-001.png"
    manifest = {
        "section_titles": ["一、One"],
        "chapter_files": ["docs/01-one.md"],
        "question_count": 1,
        "question_titles_sha256": sha256(title.encode()).hexdigest(),
        "chapter_sha256": {
            "docs/01-one.md": sha256(chapter.read_text("utf-8").encode()).hexdigest()
        },
        "site_index_sha256": sha256(
            site_index.read_text("utf-8").encode()
        ).hexdigest(),
        "image_count": 1,
        "images": [
            {
                "path": "assets/images/note-001.png",
                "sha256": sha256(image.read_bytes()).hexdigest(),
            }
        ],
    }
    (root / "tools" / "content_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
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

    def test_reports_markdown_link_that_escapes_repository_root(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root.parent / "outside.txt").write_text("outside", encoding="utf-8")
            (root / "README.md").write_text(
                "[outside](../outside.txt)", encoding="utf-8"
            )
            self.assertIn("outside repository", "\n".join(validate(root)))

    def test_reports_absolute_markdown_link(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            target = (root / "assets" / "images" / "note-001.png").as_posix()
            (root / "README.md").write_text(
                f"[absolute]({target})", encoding="utf-8"
            )
            self.assertIn("absolute link", "\n".join(validate(root)))

    def test_reports_remote_youdao_runtime_reference(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "site" / "index.html").write_text(
                '<img src="https://share.note.youdao.com/image">',
                encoding="utf-8",
            )
            self.assertIn("forbidden URL", "\n".join(validate(root)))

    def test_reports_remote_references_in_nested_site_assets(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            nested = root / "site" / "assets"
            nested.mkdir()
            (root / "site" / "index.html").write_text(
                '<img src = "https://example.com/quoted.png">',
                encoding="utf-8",
            )
            (nested / "reader.html").write_text(
                "<script src=https://example.com/app.js></script>",
                encoding="utf-8",
            )
            (nested / "theme.css").write_text(
                ".hero { background: url(https://example.com/bg.png); }",
                encoding="utf-8",
            )
            errors = "\n".join(validate(root))
            self.assertIn("index.html", errors)
            self.assertIn("reader.html", errors)
            self.assertIn("theme.css", errors)

    def test_reports_protocol_relative_site_references(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "site" / "protocol.html").write_text(
                '<script src="//cdn.example.com/app.js"></script>',
                encoding="utf-8",
            )
            (root / "site" / "protocol.css").write_text(
                ".hero { background: url(//cdn.example.com/bg.png); }",
                encoding="utf-8",
            )
            errors = "\n".join(validate(root))
            self.assertIn("protocol.html", errors)
            self.assertIn("protocol.css", errors)

    def test_reports_remote_reference_after_invalid_utf8_byte(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "site" / "broken.html").write_bytes(
                b'\xff<script src="https://example.com/app.js"></script>'
            )
            self.assertIn("broken.html", "\n".join(validate(root)))

    def test_reports_remote_fetch_and_srcset_runtime_references(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "site" / "app.js").write_text(
                'fetch("https://cdn.example.com/data.json");', encoding="utf-8"
            )
            site_index = root / "site" / "index.html"
            site_index.write_text(
                site_index.read_text("utf-8")
                + '<source srcset="//cdn.example.com/a.png 1x, local.png 2x">',
                encoding="utf-8",
            )
            errors = "\n".join(validate(root))
            self.assertIn("app.js", errors)
            self.assertIn("srcset", errors)

    def test_reports_remote_css_import(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "site" / "styles.css").write_text(
                '@import "https://cdn.example.com/theme.css";', encoding="utf-8"
            )
            self.assertIn("styles.css", "\n".join(validate(root)))

    def test_reports_missing_local_site_resource(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            site_index = root / "site" / "index.html"
            site_index.write_text(
                site_index.read_text("utf-8").replace("app.js", "missing.js"),
                encoding="utf-8",
            )
            self.assertIn("missing site asset", "\n".join(validate(root)))

    def test_reports_site_resource_path_escape(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "outside.js").write_text("const outside = true;", encoding="utf-8")
            site_index = root / "site" / "index.html"
            site_index.write_text(
                site_index.read_text("utf-8").replace("app.js", "../outside.js"),
                encoding="utf-8",
            )
            self.assertIn("outside _site", "\n".join(validate(root)))

    def test_reports_question_manifest_mismatch(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            chapter = root / "docs" / "01-one.md"
            chapter.write_text("# 一、One\n\n## 2.不同问题\n", encoding="utf-8")
            self.assertIn("question title hash", "\n".join(validate(root)))

    def test_reports_section_title_mismatch(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            chapter = root / "docs" / "01-one.md"
            chapter.write_text(
                chapter.read_text("utf-8").replace("# 一、One", "# 二、Wrong"),
                encoding="utf-8",
            )
            self.assertIn("section titles", "\n".join(validate(root)))

    def test_reports_changed_chapter_body(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            chapter = root / "docs" / "01-one.md"
            chapter.write_text(
                chapter.read_text("utf-8").replace("## 1.问题一", "## 1.问题一\n\n篡改答案"),
                encoding="utf-8",
            )
            self.assertIn("chapter SHA-256", "\n".join(validate(root)))

    def test_reports_stale_site_index(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            site_index = root / "site" / "index.html"
            site_index.write_text(
                site_index.read_text("utf-8") + "<p>stale</p>", encoding="utf-8"
            )
            self.assertIn("site/index.html SHA-256", "\n".join(validate(root)))

    def test_reports_corrupt_expected_image_and_unexpected_image_file(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            (root / "assets" / "images" / "note-001.png").write_bytes(b"garbage")
            (root / "assets" / "images" / "extra.bin").write_bytes(b"extra")
            errors = "\n".join(validate(root))
            self.assertIn("image file list", errors)
            self.assertIn("image SHA-256", errors)
            self.assertIn("invalid image", errors)

    def test_reports_missing_or_duplicate_image_references(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            write_valid_fixture(root)
            chapter = root / "docs" / "01-one.md"
            chapter.write_text(
                chapter.read_text("utf-8").replace(
                    "![图片](../assets/images/note-001.png)\n", ""
                ),
                encoding="utf-8",
            )
            site_index = root / "site" / "index.html"
            site_index.write_text(
                site_index.read_text("utf-8")
                + '<img src="assets/images/note-001.png">',
                encoding="utf-8",
            )
            errors = "\n".join(validate(root))
            self.assertIn("Markdown image reference", errors)
            self.assertIn("site image reference", errors)


if __name__ == "__main__":
    unittest.main()
