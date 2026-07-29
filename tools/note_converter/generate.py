"""Generate GitHub-readable Markdown from a saved Youdao note snapshot."""

import argparse
from pathlib import Path

from .images import materialize_images
from .markdown import render_chapters, render_readme
from .parser import parse_snapshot


def generate(snapshot: Path, image_cache: Path, repo_root: Path) -> None:
    """Materialize local images and write the README plus ten Markdown chapters."""
    note = parse_snapshot(snapshot.read_text(encoding="utf-8"), require_complete=True)
    image_paths = materialize_images(
        note, image_cache, repo_root / "assets" / "images"
    )
    (repo_root / "README.md").write_text(render_readme(note), encoding="utf-8")
    for relative_path, content in render_chapters(note, image_paths).items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--image-cache", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    args = parser.parse_args()
    snapshot = args.snapshot.resolve()
    image_cache = args.image_cache.resolve()
    repo_root = args.repo_root.resolve()

    if not snapshot.is_file():
        parser.error(f"snapshot does not exist: {snapshot}")
    if not image_cache.is_dir():
        parser.error(f"image cache directory does not exist: {image_cache}")
    generate(snapshot, image_cache, repo_root)


if __name__ == "__main__":
    main()
