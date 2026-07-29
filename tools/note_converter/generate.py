"""Generate GitHub-readable Markdown from a saved Youdao note snapshot."""

import argparse
from hashlib import sha256
import json
from pathlib import Path

from .images import materialize_images
from .markdown import render_chapters, render_readme
from .model import Note
from .parser import parse_snapshot
from .site import render_site


def build_manifest(
    note: Note,
    chapters: dict[str, str],
    site_html: str,
    image_paths: dict[str, str],
    repo_root: Path,
) -> dict[str, object]:
    """Describe every generated content and image artifact by exact digest."""
    ordered_images = [
        image_paths[block.text]
        for section in note.sections
        for block in section.blocks
        if block.kind == "image"
    ]
    if len(ordered_images) != len(set(ordered_images)):
        raise ValueError("generated image paths must be unique")
    return {
        "section_titles": [section.title for section in note.sections],
        "chapter_files": list(chapters),
        "question_count": len(note.questions),
        "question_titles_sha256": sha256(
            "\n".join(note.questions).encode()
        ).hexdigest(),
        "chapter_sha256": {
            path: sha256(content.encode()).hexdigest()
            for path, content in chapters.items()
        },
        "site_index_sha256": sha256(site_html.encode()).hexdigest(),
        "image_count": len(ordered_images),
        "images": [
            {
                "path": path,
                "sha256": sha256((repo_root / path).read_bytes()).hexdigest(),
            }
            for path in ordered_images
        ],
    }


def generate(snapshot: Path, image_cache: Path, repo_root: Path) -> None:
    """Materialize local images and write Markdown chapters plus the reader site."""
    note = parse_snapshot(snapshot.read_text(encoding="utf-8"), require_complete=True)
    image_paths = materialize_images(
        note, image_cache, repo_root / "assets" / "images"
    )
    (repo_root / "README.md").write_text(render_readme(note), encoding="utf-8")
    chapters = render_chapters(note, image_paths)
    for relative_path, content in chapters.items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    site_dir = repo_root / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    site_html = render_site(note, image_paths)
    (site_dir / "index.html").write_text(site_html, encoding="utf-8")
    manifest = build_manifest(note, chapters, site_html, image_paths, repo_root)
    (repo_root / "tools" / "content_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


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
