from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from tools.note_converter.generate import build_manifest
from tools.note_converter.model import Block, Note, Section


class GenerationTests(unittest.TestCase):
    def test_builds_manifest_for_all_generated_content_and_images(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            image_path = root / "assets" / "images" / "note-001.png"
            image_path.parent.mkdir(parents=True)
            Image.new("RGB", (2, 2), "blue").save(image_path)
            note = Note(
                "Notes",
                ("1. Question",),
                (
                    Section(
                        "01-one",
                        "One",
                        (
                            Block("paragraph", "1. Question"),
                            Block("paragraph", "Answer"),
                            Block("image", "source-1"),
                        ),
                    ),
                ),
            )
            chapters = {"docs/01-one.md": "# One\n\nAnswer\n"}
            site_html = '<img src="assets/images/note-001.png">'

            manifest = build_manifest(
                note,
                chapters,
                site_html,
                {"source-1": "assets/images/note-001.png"},
                root,
            )

            self.assertEqual(["One"], manifest["section_titles"])
            self.assertEqual(
                sha256(chapters["docs/01-one.md"].encode()).hexdigest(),
                manifest["chapter_sha256"]["docs/01-one.md"],
            )
            self.assertEqual(
                sha256(site_html.encode()).hexdigest(),
                manifest["site_index_sha256"],
            )
            self.assertEqual(
                [
                    {
                        "path": "assets/images/note-001.png",
                        "sha256": sha256(image_path.read_bytes()).hexdigest(),
                    }
                ],
                manifest["images"],
            )


if __name__ == "__main__":
    unittest.main()
