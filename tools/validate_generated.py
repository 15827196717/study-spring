from collections import Counter
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path, PurePosixPath
import posixpath
import re
from urllib.parse import unquote, urlsplit

from PIL import Image


MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
SECTION_HEADING = re.compile(r"^# (.+)$", re.MULTILINE)
QUESTION_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)
REMOTE_URL = re.compile(r"^(?:https?:)?//", re.IGNORECASE)
CSS_URL = re.compile(r"url\(\s*[\"']?([^\"')\s]+)", re.IGNORECASE)
CSS_IMPORT = re.compile(
    r"@import\s+(?!url\()[\"']([^\"']+)[\"']", re.IGNORECASE
)
JS_STRING_URL = re.compile(r"[\"']((?:https?:)?//[^\"']+)[\"']", re.IGNORECASE)
JS_RUNTIME_CALL = re.compile(
    r"\b(?:fetch|importScripts|import)\s*\(\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)
SITE_TEXT_EXTENSIONS = frozenset(
    {
        ".css",
        ".html",
        ".htm",
        ".js",
        ".json",
        ".mjs",
        ".svg",
        ".txt",
        ".webmanifest",
    }
)
HTML_RUNTIME_ATTRIBUTES = {
    "audio": {"src"},
    "embed": {"src"},
    "iframe": {"src"},
    "img": {"src", "srcset"},
    "input": {"src"},
    "link": {"href"},
    "object": {"data"},
    "script": {"src"},
    "source": {"src", "srcset"},
    "video": {"poster", "src"},
}


def _srcset_urls(value: str) -> list[str]:
    return [
        candidate.strip().split()[0]
        for candidate in value.split(",")
        if candidate.strip()
    ]


class _RuntimeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str]] = []
        self.image_sources: list[str] = []
        self.inline_css: list[str] = []
        self.inline_js: list[str] = []
        self._text_mode: str | None = None

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._record_tag(tag, attrs)
        if tag in {"style", "script"}:
            self._text_mode = tag

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        self._record_tag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag == self._text_mode:
            self._text_mode = None

    def handle_data(self, data: str) -> None:
        if self._text_mode == "style":
            self.inline_css.append(data)
        elif self._text_mode == "script":
            self.inline_js.append(data)

    def _record_tag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        runtime_attrs = HTML_RUNTIME_ATTRIBUTES.get(tag, set())
        for name, value in attrs:
            if value is None:
                continue
            if name == "style":
                self.inline_css.append(value)
            if name not in runtime_attrs:
                continue
            values = _srcset_urls(value) if name == "srcset" else [value]
            for target in values:
                self.references.append((f"{tag} {name}", target))
                if tag == "img" and name == "src":
                    self.image_sources.append(target)


def _is_remote(target: str) -> bool:
    return bool(REMOTE_URL.match(target.strip()))


def _ignored_runtime_target(target: str) -> bool:
    lowered = target.strip().lower()
    return (
        not lowered
        or lowered.startswith("#")
        or lowered.startswith("data:")
        or lowered.startswith("blob:")
        or lowered.startswith("javascript:")
    )


def _virtual_source(
    repo_root: Path,
    referring_virtual_path: str,
    raw_target: str,
    errors: list[str],
    context: str,
) -> Path | None:
    if _is_remote(raw_target):
        errors.append(f"forbidden URL in {context}: {raw_target}")
        return None
    if _ignored_runtime_target(raw_target):
        return None

    target = unquote(urlsplit(raw_target).path).replace("\\", "/")
    if re.match(r"^[A-Za-z]:", target):
        errors.append(f"site asset outside _site in {context}: {raw_target}")
        return None
    if target.startswith("/"):
        virtual_path = target.lstrip("/")
    else:
        virtual_path = posixpath.join(
            str(PurePosixPath(referring_virtual_path).parent), target
        )
    virtual_path = posixpath.normpath(virtual_path)
    if virtual_path == ".." or virtual_path.startswith("../"):
        errors.append(f"site asset outside _site in {context}: {raw_target}")
        return None

    if virtual_path == "assets/images" or virtual_path.startswith(
        "assets/images/"
    ):
        source = repo_root / PurePosixPath(virtual_path)
        allowed_root = (repo_root / "assets" / "images").resolve()
    else:
        source = repo_root / "site" / PurePosixPath(virtual_path)
        allowed_root = (repo_root / "site").resolve()
    resolved = source.resolve()
    try:
        resolved.relative_to(allowed_root)
    except ValueError:
        errors.append(f"site asset outside _site in {context}: {raw_target}")
        return None
    if not resolved.is_file():
        errors.append(f"missing site asset in {context}: {raw_target}")
        return None
    return resolved


def _css_references(text: str) -> list[str]:
    return CSS_URL.findall(text) + CSS_IMPORT.findall(text)


def _validate_runtime_text(
    repo_root: Path,
    virtual_path: str,
    source_name: str,
    text: str,
    errors: list[str],
) -> None:
    suffix = PurePosixPath(virtual_path).suffix.lower()
    if "share.note.youdao.com" in text:
        errors.append(f"forbidden URL in {source_name}")
    if suffix == ".css":
        for target in _css_references(text):
            _virtual_source(repo_root, virtual_path, target, errors, source_name)
    elif suffix in {".js", ".mjs"}:
        for target in JS_STRING_URL.findall(text):
            errors.append(f"forbidden URL in {source_name}: {target}")
        for target in JS_RUNTIME_CALL.findall(text):
            if not _is_remote(target):
                _virtual_source(
                    repo_root, virtual_path, target, errors, source_name
                )


def _validate_site(repo_root: Path, errors: list[str]) -> Counter[str]:
    site_dir = repo_root / "site"
    site_images: Counter[str] = Counter()
    for site_path in site_dir.rglob("*"):
        if (
            not site_path.is_file()
            or site_path.suffix.lower() not in SITE_TEXT_EXTENSIONS
        ):
            continue
        text = site_path.read_text("utf-8", errors="replace")
        virtual_path = site_path.relative_to(site_dir).as_posix()
        _validate_runtime_text(
            repo_root, virtual_path, virtual_path, text, errors
        )
        if site_path.suffix.lower() not in {".html", ".htm"}:
            continue

        parser = _RuntimeHTMLParser()
        parser.feed(text)
        for label, target in parser.references:
            resolved = _virtual_source(
                repo_root,
                virtual_path,
                target,
                errors,
                f"{virtual_path} {label}",
            )
            if resolved is not None and label == "img src":
                site_images[resolved.relative_to(repo_root).as_posix()] += 1
        for css in parser.inline_css:
            for target in _css_references(css):
                _virtual_source(
                    repo_root, virtual_path, target, errors, virtual_path
                )
        for script in parser.inline_js:
            for target in JS_STRING_URL.findall(script):
                errors.append(f"forbidden URL in {virtual_path}: {target}")
            for target in JS_RUNTIME_CALL.findall(script):
                if not _is_remote(target):
                    _virtual_source(
                        repo_root, virtual_path, target, errors, virtual_path
                    )
    return site_images


def validate(repo_root: Path) -> list[str]:
    """Return all internal-consistency errors in generated notes artifacts."""
    repo_root = repo_root.resolve()
    errors: list[str] = []
    manifest = json.loads(
        (repo_root / "tools" / "content_manifest.json").read_text("utf-8")
    )

    chapter_paths = [repo_root / path for path in manifest["chapter_files"]]
    for chapter in chapter_paths:
        if not chapter.exists():
            errors.append(f"missing chapter: {chapter.relative_to(repo_root)}")

    existing_chapters = [path for path in chapter_paths if path.exists()]
    chapter_text = {
        path.relative_to(repo_root).as_posix(): path.read_text("utf-8")
        for path in existing_chapters
    }
    section_titles = [
        match.group(1) if (match := SECTION_HEADING.search(text)) else ""
        for text in chapter_text.values()
    ]
    if section_titles != manifest["section_titles"]:
        errors.append("section titles do not match source manifest")

    question_titles = [
        title
        for text in chapter_text.values()
        for title in QUESTION_HEADING.findall(text)
    ]
    actual_hash = sha256("\n".join(question_titles).encode()).hexdigest()
    if len(question_titles) != manifest["question_count"]:
        errors.append(
            f"expected {manifest['question_count']} question headings, "
            f"got {len(question_titles)}"
        )
    if actual_hash != manifest["question_titles_sha256"]:
        errors.append("question title hash does not match source manifest")

    chapter_hashes = manifest["chapter_sha256"]
    if set(chapter_hashes) != set(manifest["chapter_files"]):
        errors.append("chapter SHA-256 manifest keys do not match chapter files")
    for relative_path, text in chapter_text.items():
        if sha256(text.encode()).hexdigest() != chapter_hashes.get(relative_path):
            errors.append(f"chapter SHA-256 mismatch: {relative_path}")

    site_index = repo_root / "site" / "index.html"
    if not site_index.is_file():
        errors.append("missing site asset: site/index.html")
    elif sha256(site_index.read_text("utf-8").encode()).hexdigest() != manifest[
        "site_index_sha256"
    ]:
        errors.append("site/index.html SHA-256 does not match source manifest")

    expected_images = manifest["images"]
    expected_image_paths = [item["path"] for item in expected_images]
    expected_image_set = set(expected_image_paths)
    image_dir = repo_root / "assets" / "images"
    actual_image_paths = sorted(
        path.relative_to(repo_root).as_posix()
        for path in image_dir.rglob("*")
        if path.is_file()
    )
    if len(actual_image_paths) != manifest["image_count"]:
        errors.append(
            f"expected {manifest['image_count']} images, "
            f"got {len(actual_image_paths)}"
        )
    if actual_image_paths != sorted(expected_image_paths):
        errors.append("image file list does not match source manifest")
    for image_info in expected_images:
        image_path = repo_root / image_info["path"]
        if not image_path.is_file():
            continue
        if sha256(image_path.read_bytes()).hexdigest() != image_info["sha256"]:
            errors.append(f"image SHA-256 mismatch: {image_info['path']}")
        try:
            with Image.open(image_path) as image:
                image.verify()
        except (OSError, SyntaxError):
            errors.append(f"invalid image: {image_info['path']}")

    markdown_paths = [repo_root / "README.md", *existing_chapters]
    markdown_images: Counter[str] = Counter()
    for markdown_path in markdown_paths:
        if not markdown_path.exists():
            errors.append(f"missing Markdown file: {markdown_path.name}")
            continue
        text = markdown_path.read_text("utf-8")
        if "share.note.youdao.com" in text:
            errors.append(f"forbidden URL in {markdown_path.name}")
        for raw_target in MARKDOWN_IMAGE.findall(text):
            target = raw_target.strip("<>").split("#", 1)[0]
            if _is_remote(target):
                errors.append(
                    f"forbidden URL in {markdown_path.name}: {raw_target}"
                )
                continue
            target_path = Path(unquote(target))
            if not target_path.is_absolute():
                resolved = (markdown_path.parent / target_path).resolve()
                try:
                    relative = resolved.relative_to(repo_root).as_posix()
                except ValueError:
                    continue
                markdown_images[relative] += 1
        for raw_target in MARKDOWN_LINK.findall(text):
            target = raw_target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^(?:https?|mailto):", target):
                continue
            target_path = Path(unquote(target))
            if target_path.is_absolute():
                errors.append(
                    f"absolute link in {markdown_path.name}: {raw_target}"
                )
                continue
            resolved = (markdown_path.parent / target_path).resolve()
            try:
                resolved.relative_to(repo_root)
            except ValueError:
                errors.append(
                    f"link outside repository in {markdown_path.name}: "
                    f"{raw_target}"
                )
                continue
            if not resolved.exists():
                errors.append(
                    f"broken link in {markdown_path.name}: {raw_target}"
                )

    for image_path in expected_image_paths:
        count = markdown_images[image_path]
        if count != 1:
            errors.append(
                f"Markdown image reference count for {image_path}: "
                f"expected 1, got {count}"
            )
    for image_path in markdown_images.keys() - expected_image_set:
        errors.append(f"unexpected Markdown image reference: {image_path}")

    site_images = _validate_site(repo_root, errors)
    for image_path in expected_image_paths:
        count = site_images[image_path]
        if count != 1:
            errors.append(
                f"site image reference count for {image_path}: "
                f"expected 1, got {count}"
            )
    for image_path in site_images.keys() - expected_image_set:
        errors.append(f"unexpected site image reference: {image_path}")

    return errors


if __name__ == "__main__":
    import sys

    found = validate(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
    if found:
        for error in found:
            print(f"ERROR: {error}")
        raise SystemExit(1)
    print("PASS: generated content is internally consistent")
