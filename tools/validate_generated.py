from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import unquote


MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
QUESTION_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)
FORBIDDEN_SITE_REFERENCE = re.compile(
    r"(?:src|href)=\s*[\"']https?://|url\(\s*[\"']?https?://",
    re.IGNORECASE,
)


def validate(repo_root: Path) -> list[str]:
    """Return all internal-consistency errors in generated notes artifacts."""
    errors: list[str] = []
    manifest = json.loads(
        (repo_root / "tools" / "content_manifest.json").read_text("utf-8")
    )

    chapter_paths = [repo_root / path for path in manifest["chapter_files"]]
    for chapter in chapter_paths:
        if not chapter.exists():
            errors.append(f"missing chapter: {chapter.relative_to(repo_root)}")

    existing_chapters = [path for path in chapter_paths if path.exists()]
    question_titles = [
        title
        for chapter in existing_chapters
        for title in QUESTION_HEADING.findall(chapter.read_text("utf-8"))
    ]
    actual_hash = sha256("\n".join(question_titles).encode()).hexdigest()
    if len(question_titles) != manifest["question_count"]:
        errors.append(
            f"expected {manifest['question_count']} question headings, "
            f"got {len(question_titles)}"
        )
    if actual_hash != manifest["question_titles_sha256"]:
        errors.append("question title hash does not match source manifest")

    image_dir = repo_root / "assets" / "images"
    images = sorted(path for path in image_dir.glob("*") if path.is_file())
    if len(images) != manifest["image_count"]:
        errors.append(
            f"expected {manifest['image_count']} images, got {len(images)}"
        )

    markdown_paths = [repo_root / "README.md", *existing_chapters]
    for markdown_path in markdown_paths:
        if not markdown_path.exists():
            errors.append(f"missing Markdown file: {markdown_path.name}")
            continue
        text = markdown_path.read_text("utf-8")
        if "share.note.youdao.com" in text:
            errors.append(f"forbidden URL in {markdown_path.name}")
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^(?:https?|mailto):", target):
                continue
            resolved = markdown_path.parent / unquote(target)
            if not resolved.exists():
                errors.append(f"broken link in {markdown_path.name}: {raw_target}")

    site_dir = repo_root / "site"
    for site_path in site_dir.glob("*"):
        if not site_path.is_file():
            continue
        text = site_path.read_text("utf-8")
        if "share.note.youdao.com" in text or FORBIDDEN_SITE_REFERENCE.search(text):
            errors.append(f"forbidden URL in {site_path.name}")

    return errors


if __name__ == "__main__":
    import sys

    found = validate(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
    if found:
        for error in found:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("PASS: generated content is internally consistent")
