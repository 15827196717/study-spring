from pathlib import Path
import shutil

from PIL import Image

from .model import Note

EXTENSION_PRIORITY = (".png", ".jpg", ".jpeg", ".webp")


def _source_for(index: int, cache_dir: Path) -> Path:
    for suffix in EXTENSION_PRIORITY:
        candidate = cache_dir / f"image_{index:03d}{suffix}"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(f"missing cached image image_{index:03d}")


def materialize_images(
    note: Note, cache_dir: Path, output_dir: Path
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    mapping: dict[str, str] = {}
    urls = [
        block.text
        for section in note.sections
        for block in section.blocks
        if block.kind == "image"
    ]
    for index, url in enumerate(urls, start=1):
        source = _source_for(index, cache_dir)
        if source.suffix.lower() == ".webp":
            target = output_dir / f"note-{index:03d}.png"
            with Image.open(source) as image:
                image.convert("RGB").save(target, "PNG")
        else:
            suffix = ".jpg" if source.suffix.lower() == ".jpeg" else source.suffix.lower()
            target = output_dir / f"note-{index:03d}{suffix}"
            shutil.copy2(source, target)
        mapping[url] = f"assets/images/{target.name}"
    return mapping
