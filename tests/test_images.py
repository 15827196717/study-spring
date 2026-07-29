from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image

from tools.note_converter.images import materialize_images
from tools.note_converter.model import Block, Note, Section


def note_with_images(count: int) -> Note:
    blocks = tuple(
        Block("image", f"https://source.invalid/image/{index}")
        for index in range(1, count + 1)
    )
    return Note("title", (), (Section("01-one", "One", blocks),))


class ImageTests(unittest.TestCase):
    def test_copies_jpeg_and_converts_webp(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            output = root / "assets" / "images"
            cache.mkdir()
            Image.new("RGB", (8, 8), "red").save(cache / "image_001.jpg")
            Image.new("RGB", (8, 8), "blue").save(cache / "image_002.webp")

            mapping = materialize_images(note_with_images(2), cache, output)

            self.assertEqual(2, len(mapping))
            self.assertTrue((output / "note-001.jpg").exists())
            self.assertTrue((output / "note-002.png").exists())

    def test_reports_the_exact_missing_cache_entry(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            cache = root / "cache"
            cache.mkdir()
            Image.new("RGB", (8, 8), "red").save(cache / "image_001.jpg")
            Image.new("RGB", (8, 8), "blue").save(cache / "image_002.png")
            with self.assertRaisesRegex(FileNotFoundError, "image_003"):
                materialize_images(note_with_images(3), cache, root / "output")


if __name__ == "__main__":
    unittest.main()
