# GitHub-Readable Spring Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the extracted Youdao Spring interview note into GitHub-native Markdown chapters with local images, add an optional enhanced static reading site, and publish both through `15827196717/study-spring`.

**Architecture:** A small Python conversion package parses the saved accessibility snapshot into a typed document model. Two renderers consume the same model: one generates the repository `README.md` and ten Markdown chapters, while the other generates semantic static HTML. A validator checks source fidelity, local links, image coverage, and external-resource isolation before GitHub Actions packages the static site for Pages.

**Tech Stack:** Python 3.11+, standard-library `unittest`, Pillow 12.x, HTML/CSS/vanilla JavaScript, GitHub Actions, GitHub Pages.

## Global Constraints

- The primary reading path must work entirely on `github.com`; Pages is optional.
- The company network is assumed to allow `github.com` but may block `github.io`.
- Do not load Youdao images, external fonts, CDNs, analytics, or third-party JavaScript at runtime.
- Preserve the source wording and original numbering, including missing or duplicated question numbers.
- Generate exactly ten topic chapters and retain all 69 extracted images.
- The source table of contents contains 97 question headings; its normalized SHA-256 is `af69f6acea9a863897f96921926f34a6bdc8f7e1708ad6e441b09f69b97ef434`.
- Keep `最新Spring全家桶面试题—图灵徐庶.docx` as the downloadable offline version.
- Do not modify the existing `二、框架源码专题/` material.
- Use repository-relative links in Markdown and site-relative links in Pages.

---

## File Structure

### Files to create

- `README.md` — repository landing page, learning entry points, chapter links, and download link.
- `docs/01-spring-framework.md` through `docs/10-microservices.md` — GitHub-native reading chapters.
- `assets/images/*` — 69 locally hosted note images.
- `tools/note_converter/__init__.py` — public package exports.
- `tools/note_converter/model.py` — immutable note, section, and block data types.
- `tools/note_converter/parser.py` — snapshot-to-model parser.
- `tools/note_converter/images.py` — cached-image selection and WebP conversion.
- `tools/note_converter/markdown.py` — README and chapter rendering.
- `tools/note_converter/site.py` — semantic HTML rendering.
- `tools/note_converter/generate.py` — command-line orchestration.
- `tools/validate_generated.py` — generated-output integrity and link checks.
- `tools/content_manifest.json` — exact section, question, and image expectations.
- `tests/fixtures/minimal_snapshot.txt` — compact parser fixture.
- `tests/test_parser.py` — parser behavior and numbering tests.
- `tests/test_images.py` — deterministic image selection/conversion tests.
- `tests/test_markdown.py` — README/chapter rendering tests.
- `tests/test_site.py` — static HTML contract tests.
- `tests/test_validation.py` — broken-link and integrity regression tests.
- `requirements-dev.txt` — pinned conversion/test dependencies.
- `.gitignore` — ignores the local `_site/` preview artifact.
- `site/index.html` — generated enhanced reader.
- `site/styles.css` — responsive reader styles.
- `site/app.js` — search, active navigation, theme, progress, and back-to-top behavior.
- `.github/workflows/pages.yml` — validation and Pages deployment workflow.

### Files already present and left unchanged

- `最新Spring全家桶面试题—图灵徐庶.docx`
- `二、框架源码专题/**`
- `docs/superpowers/specs/2026-07-29-github-readable-spring-notes-design.md`

### Local generation inputs

- `../youdao_note_snapshot.txt`
- `../youdao_images/`

These inputs are local conversion sources and are not committed because the generated Markdown and repository-local images are the maintained deliverables.

---

### Task 1: Parse the Youdao Snapshot into a Typed Document Model

**Files:**
- Create: `tools/note_converter/__init__.py`
- Create: `tools/note_converter/model.py`
- Create: `tools/note_converter/parser.py`
- Create: `tests/fixtures/minimal_snapshot.txt`
- Create: `tests/test_parser.py`
- Create: `requirements-dev.txt`

**Interfaces:**
- Produces: `Block`, `Section`, and `Note` immutable dataclasses.
- Produces: `parse_snapshot(snapshot: str) -> Note`.
- Produces: `question_titles(note: Note) -> list[str]`.
- Consumes: UTF-8 snapshot text in the same line-oriented format as `../youdao_note_snapshot.txt`.

- [ ] **Step 1: Create the failing parser fixture**

Create `tests/fixtures/minimal_snapshot.txt` with this exact shape:

```text
- generic "page chrome"
- iframe:
  - generic: Spring最新全家桶面试题
  - generic: 一、Spring Framework
  - generic: 1.问题一
  - generic: 二、Spring IOC
  - generic: 2.问题二
  - generic: 一、Spring Framework
  - generic: 1.问题一
  - generic: 答案一
  - code: public
  - code
  - code: class
  - code: Demo
  - img "https://share.note.youdao.com/yws/public/resource/example/1"
  - generic: 二、Spring IOC
  - generic: 2.问题二
  - list:
    - generic: 答案二
- paragraph: footer
```

- [ ] **Step 2: Write failing model and parser tests**

Create `tests/test_parser.py`:

```python
from pathlib import Path
import unittest

from tools.note_converter.parser import parse_snapshot, question_titles


FIXTURE = Path(__file__).parent / "fixtures" / "minimal_snapshot.txt"


class ParserTests(unittest.TestCase):
    def setUp(self):
        self.note = parse_snapshot(FIXTURE.read_text(encoding="utf-8"))

    def test_skips_source_table_of_contents_and_uses_detailed_body(self):
        self.assertEqual("Spring最新全家桶面试题", self.note.title)
        self.assertEqual(["一、Spring Framework", "二、Spring IOC"],
                         [section.title for section in self.note.sections])
        self.assertEqual(["1.问题一", "2.问题二"], question_titles(self.note))

    def test_preserves_code_image_and_bullet_blocks(self):
        kinds = [block.kind for section in self.note.sections
                 for block in section.blocks]
        self.assertIn("code", kinds)
        self.assertIn("image", kinds)
        self.assertIn("bullet", kinds)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the parser tests and verify the expected failure**

Run:

```powershell
python -m unittest tests.test_parser -v
```

Expected: `ImportError` or `ModuleNotFoundError` for `tools.note_converter`.

- [ ] **Step 4: Implement the immutable model**

Create `tools/note_converter/model.py`:

```python
from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["paragraph", "bullet", "code", "image"]


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    text: str


@dataclass(frozen=True)
class Section:
    slug: str
    title: str
    blocks: tuple[Block, ...]


@dataclass(frozen=True)
class Note:
    title: str
    questions: tuple[str, ...]
    sections: tuple[Section, ...]
```

Create `tools/note_converter/__init__.py` exporting `Block`, `Section`, `Note`, `parse_snapshot`, and `question_titles`.

- [ ] **Step 5: Implement the minimal parser**

In `tools/note_converter/parser.py`:

```python
import json
import re

from .model import Block, Note, Section

SECTION_FILES = (
    ("一、Spring Framework", "01-spring-framework"),
    ("二、Spring IOC", "02-spring-ioc"),
    ("三、Spring Beans", "03-spring-beans"),
    ("四、Spring注解", "04-spring-annotations"),
    ("五、Spring AOP", "05-spring-aop"),
    ("六、Spring事务", "06-spring-transactions"),
    ("七、Spring其他", "07-spring-other"),
    ("八、SpringMVC", "08-spring-mvc"),
    ("九、Spring Boot", "09-spring-boot"),
    ("十、微服务", "10-microservices"),
)


def _decode(value: str) -> str:
    value = value.strip()
    if value.startswith('"') and value.endswith('"'):
        return json.loads(value)
    return value


def parse_snapshot(snapshot: str) -> Note:
    # Restrict parsing to the single iframe subtree.
    frame = snapshot.split("- iframe:\n", 1)[1].split("\n- paragraph:", 1)[0]
    lines = frame.splitlines()
    title = _decode(lines[0].split("generic:", 1)[1])

    # The first section sequence is the source TOC; the second occurrence
    # of the first section begins the detailed body.
    first_heading = "  - generic: 一、Spring Framework"
    starts = [index for index, line in enumerate(lines) if line == first_heading]
    if len(starts) != 2:
        raise ValueError(f"expected two first-section markers, got {len(starts)}")
    questions = tuple(
        _decode(match.group(1))
        for line in lines[starts[0]:starts[1]]
        if (match := re.match(r"^  - generic:\s?(.*)$", line))
        and re.match(r"^\d+[.、]", _decode(match.group(1)))
    )
    body = lines[starts[1]:]

    # Walk body lines, group consecutive code tokens, and create sections
    # only from the exact SECTION_FILES titles.
    section_slugs = dict(SECTION_FILES)
    sections: list[Section] = []
    current_title: str | None = None
    current_blocks: list[Block] = []
    code_tokens: list[str] = []

    def flush_code() -> None:
        nonlocal code_tokens
        if not code_tokens:
            return
        parts: list[str] = []
        blanks = 0
        for token in code_tokens:
            if not token:
                blanks += 1
                continue
            if blanks >= 2 and parts:
                parts.append("\n")
            elif blanks == 1 and parts and parts[-1] != "\n":
                parts.append(" ")
            parts.append(token)
            blanks = 0
        code = "".join(parts).strip()
        if code:
            current_blocks.append(Block("code", code))
        code_tokens = []

    def flush_section() -> None:
        nonlocal current_blocks
        if current_title is not None:
            sections.append(
                Section(
                    section_slugs[current_title],
                    current_title,
                    tuple(current_blocks),
                )
            )
        current_blocks = []

    for line in body:
        code_match = re.match(r"^\s+- code(?::\s?(.*))?$", line)
        if code_match:
            raw = code_match.group(1)
            code_tokens.append(_decode(raw) if raw is not None else "")
            continue
        flush_code()

        image_match = re.match(r'^\s+- img "(https://[^"]+)"$', line)
        if image_match:
            if current_title is not None:
                current_blocks.append(Block("image", image_match.group(1)))
            continue

        text_match = re.match(
            r"^(\s+)- (?:generic|paragraph):\s?(.*)$", line
        )
        if not text_match:
            continue
        indent, raw = text_match.groups()
        text = _decode(raw).strip()
        if text in section_slugs:
            flush_section()
            current_title = text
        elif text and current_title is not None:
            kind = "bullet" if len(indent) >= 4 else "paragraph"
            current_blocks.append(Block(kind, text))

    flush_code()
    flush_section()
    return Note(title, questions, tuple(sections))


def question_titles(note: Note) -> list[str]:
    return list(note.questions)
```

The parser implementation must:

- recognizes exact section titles from `SECTION_FILES`;
- converts four-space nested `generic` entries to `bullet`;
- groups consecutive `code` entries into one code block, using two empty code tokens as a line break and one as a space;
- converts `img "URL"` to an image block;
- preserves all other two-space `generic` and `paragraph` entries as paragraph blocks;
- raises `ValueError` when content appears before a detailed section or when fewer than ten real sections are parsed in the full snapshot.

- [ ] **Step 6: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_parser -v
git diff --check
```

Expected: both parser tests pass and `git diff --check` prints nothing.

Commit:

```powershell
git add requirements-dev.txt tools/note_converter tests/fixtures/minimal_snapshot.txt tests/test_parser.py
git commit -m "feat: parse extracted Spring note"
```

---

### Task 2: Materialize All Images without External Runtime Dependencies

**Files:**
- Create: `tools/note_converter/images.py`
- Create: `tests/test_images.py`
- Modify: `requirements-dev.txt`

**Interfaces:**
- Consumes: `Note` and a local image cache containing `image_NNN.<ext>`.
- Produces: `materialize_images(note: Note, cache_dir: Path, output_dir: Path) -> dict[str, str]`.
- Mapping keys are original image URLs; values are repository-relative paths such as `assets/images/note-001.png`.

- [ ] **Step 1: Add Pillow and write failing image tests**

Set `requirements-dev.txt` to:

```text
Pillow==12.2.0
```

Create `tests/test_images.py` using `tempfile.TemporaryDirectory` and Pillow. The test must create:

- `image_001.jpg`, asserting it is copied as `note-001.jpg`;
- `image_002.webp`, asserting it is converted to `note-002.png`;
- a note containing two image blocks, asserting the returned URL mapping has two entries;
- a missing third cached image, asserting `FileNotFoundError` includes `image_003`.

Use a helper that constructs a `Note` with one section and image blocks so the test does not depend on the full snapshot.

```python
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
    return Note("title", (), (Section("01-one", "一、One", blocks),))


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
            with self.assertRaisesRegex(FileNotFoundError, "image_001"):
                materialize_images(note_with_images(1), cache, root / "output")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the image tests and verify failure**

Run:

```powershell
python -m unittest tests.test_images -v
```

Expected: import failure for `tools.note_converter.images`.

- [ ] **Step 3: Implement deterministic image selection and conversion**

Create `tools/note_converter/images.py` with:

```python
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
```

Make the returned path relative to the supplied repository root in the orchestration layer, not by using the current working directory inside this module.

- [ ] **Step 4: Run tests and commit**

Run:

```powershell
python -m unittest tests.test_images -v
git diff --check
```

Expected: all image tests pass.

Commit:

```powershell
git add requirements-dev.txt tools/note_converter/images.py tests/test_images.py
git commit -m "feat: localize note images"
```

---

### Task 3: Generate the GitHub README and Ten Markdown Chapters

**Files:**
- Create: `tools/note_converter/markdown.py`
- Create: `tools/note_converter/generate.py`
- Create: `tools/content_manifest.json`
- Create: `tests/test_markdown.py`
- Generate: `README.md`
- Generate: `docs/01-spring-framework.md` through `docs/10-microservices.md`
- Generate: `assets/images/*`

**Interfaces:**
- Consumes: `Note` and `dict[str, str]` image mapping.
- Produces: `render_chapters(note: Note, image_paths: dict[str, str]) -> dict[str, str]`.
- Produces: `render_readme(note: Note) -> str`.
- Produces CLI:
  `python -m tools.note_converter.generate --snapshot PATH --image-cache DIR --repo-root DIR`.

- [ ] **Step 1: Create the exact source manifest**

Create `tools/content_manifest.json`:

```json
{
  "section_titles": [
    "一、Spring Framework",
    "二、Spring IOC",
    "三、Spring Beans",
    "四、Spring注解",
    "五、Spring AOP",
    "六、Spring事务",
    "七、Spring其他",
    "八、SpringMVC",
    "九、Spring Boot",
    "十、微服务"
  ],
  "chapter_files": [
    "docs/01-spring-framework.md",
    "docs/02-spring-ioc.md",
    "docs/03-spring-beans.md",
    "docs/04-spring-annotations.md",
    "docs/05-spring-aop.md",
    "docs/06-spring-transactions.md",
    "docs/07-spring-other.md",
    "docs/08-spring-mvc.md",
    "docs/09-spring-boot.md",
    "docs/10-microservices.md"
  ],
  "question_count": 97,
  "question_titles_sha256": "af69f6acea9a863897f96921926f34a6bdc8f7e1708ad6e441b09f69b97ef434",
  "image_count": 69
}
```

- [ ] **Step 2: Write failing Markdown renderer tests**

Create `tests/test_markdown.py` with a two-section in-memory note and assertions that:

- `render_chapters` returns one file per section slug;
- a question paragraph becomes `## 1.问题一`;
- bullets become `- 答案`;
- code is fenced with triple backticks;
- an image URL becomes `![笔记图片 1](../assets/images/note-001.png)`;
- every chapter contains `[返回首页](../README.md)`;
- `render_readme` links the chapter, existing `二、框架源码专题/`, Word document, and optional Pages URL.

```python
import unittest

from tools.note_converter.markdown import render_chapters, render_readme
from tools.note_converter.model import Block, Note, Section


NOTE = Note(
    "Spring Notes",
    ("1.问题一", "2.问题二"),
    (
        Section(
            "01-one",
            "一、One",
            (
                Block("paragraph", "1.问题一"),
                Block("paragraph", "答案"),
                Block("bullet", "要点"),
                Block("code", "class Demo {}"),
                Block("image", "https://source.invalid/1"),
            ),
        ),
        Section(
            "02-two",
            "二、Two",
            (Block("paragraph", "2.问题二"),),
        ),
    ),
)


class MarkdownTests(unittest.TestCase):
    def test_renders_questions_blocks_images_and_navigation(self):
        chapters = render_chapters(
            NOTE, {"https://source.invalid/1": "assets/images/note-001.png"}
        )
        first = chapters["docs/01-one.md"]
        self.assertIn("## 1.问题一", first)
        self.assertIn("- 要点", first)
        self.assertIn("```\nclass Demo {}\n```", first)
        self.assertIn("../assets/images/note-001.png", first)
        self.assertIn("[返回首页](../README.md)", first)
        self.assertIn("[下一章](02-two.md)", first)

    def test_renders_repository_entry_points(self):
        readme = render_readme(NOTE)
        self.assertIn("docs/01-one.md", readme)
        self.assertIn("二、框架源码专题/", readme)
        self.assertIn("最新Spring全家桶面试题—图灵徐庶.docx", readme)
        self.assertIn("https://15827196717.github.io/study-spring/", readme)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run the Markdown tests and verify failure**

Run:

```powershell
python -m unittest tests.test_markdown -v
```

Expected: import failure for `tools.note_converter.markdown`.

- [ ] **Step 4: Implement Markdown rendering**

In `tools/note_converter/markdown.py`, implement:

```python
def render_chapters(
    note: Note, image_paths: dict[str, str]
) -> dict[str, str]:
    questions = set(note.questions)
    rendered: dict[str, str] = {}
    for index, section in enumerate(note.sections):
        lines = [f"# {section.title}", "", "[返回首页](../README.md)", ""]
        for block in section.blocks:
            if block.kind == "paragraph" and block.text in questions:
                lines.extend([f"## {block.text}", ""])
            elif block.kind == "paragraph":
                lines.extend([block.text, ""])
            elif block.kind == "bullet":
                lines.extend([f"- {block.text}", ""])
            elif block.kind == "code":
                lines.extend(["```", block.text, "```", ""])
            elif block.kind == "image":
                path = image_paths[block.text]
                lines.extend([f"![笔记图片](../{path})", ""])
        previous_link = (
            f"[上一章]({note.sections[index - 1].slug}.md)"
            if index > 0 else ""
        )
        next_link = (
            f"[下一章]({note.sections[index + 1].slug}.md)"
            if index + 1 < len(note.sections) else ""
        )
        lines.extend([f"{previous_link} · [返回首页](../README.md) · {next_link}", ""])
        rendered[f"docs/{section.slug}.md"] = "\n".join(lines)
    return rendered


def render_readme(note: Note) -> str:
    lines = [
        f"# {note.title}",
        "",
        "可直接在 GitHub 内阅读的 Spring 学习笔记。",
        "",
        "## 面试题章节",
        "",
    ]
    lines.extend(
        f"{index}. [{section.title}](docs/{section.slug}.md)"
        for index, section in enumerate(note.sections, start=1)
    )
    lines.extend([
        "",
        "## 其他资料",
        "",
        "- [Spring 框架源码专题](二、框架源码专题/)",
        "- [下载 Word 版本](最新Spring全家桶面试题—图灵徐庶.docx)",
        "- [增强版网页](https://15827196717.github.io/study-spring/)",
        "",
    ])
    return "\n".join(lines)
```

Rendering rules:

- Chapter title: `# {section.title}`.
- Question block matching `^\d+[.、]`: `## {text}`.
- Bullet: `- {text}`.
- Code: fenced block with no guessed language.
- Image: `![笔记图片 N](../{repository_relative_path})`.
- Ordinary paragraph: raw text separated by blank lines.
- Footer navigation: previous chapter, return home, next chapter.
- README includes all ten chapter links, the existing framework-source directory, the Word document, and the optional Pages URL.
- Do not embed raw HTML, scripts, remote images, or external badges in Markdown.

- [ ] **Step 5: Implement the generation CLI**

In `tools/note_converter/generate.py`:

```python
def generate(snapshot: Path, image_cache: Path, repo_root: Path) -> None:
    note = parse_snapshot(snapshot.read_text(encoding="utf-8"))
    image_paths = materialize_images(
        note, image_cache, repo_root / "assets" / "images"
    )
    chapters = render_chapters(note, image_paths)
    (repo_root / "README.md").write_text(render_readme(note), encoding="utf-8")
    for relative_path, content in chapters.items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
```

Add `argparse` options `--snapshot`, `--image-cache`, and `--repo-root`. Resolve all three to absolute paths before generation. Refuse to run when the snapshot or image-cache directory does not exist.

- [ ] **Step 6: Run tests, generate the real Markdown, and inspect counts**

Run:

```powershell
python -m unittest tests.test_markdown -v
python -m tools.note_converter.generate `
  --snapshot '..\youdao_note_snapshot.txt' `
  --image-cache '..\youdao_images' `
  --repo-root '.'
(Get-ChildItem docs -Filter '*.md' | Where-Object Name -Match '^\d{2}-').Count
(Get-ChildItem assets/images -File).Count
```

Expected:

- renderer tests pass;
- chapter count is `10`;
- image count is `69`.

- [ ] **Step 7: Commit the Markdown deliverable**

Run:

```powershell
git diff --check
git add README.md docs/*.md assets/images tools/content_manifest.json `
  tools/note_converter/markdown.py tools/note_converter/generate.py tests/test_markdown.py
git commit -m "docs: add GitHub-readable Spring interview notes"
```

---

### Task 4: Generate the Enhanced Static Reader

**Files:**
- Create: `tools/note_converter/site.py`
- Create: `tests/test_site.py`
- Generate: `site/index.html`
- Create: `site/styles.css`
- Create: `site/app.js`

**Interfaces:**
- Consumes: `Note` and the same repository-relative image mapping as Markdown.
- Produces: `render_site(note: Note, image_paths: dict[str, str]) -> str`.
- JavaScript relies on:
  - article headings carrying stable `id` attributes;
  - `[data-search-input]`, `[data-toc]`, `[data-theme-toggle]`,
    `[data-progress]`, and `[data-back-to-top]` hooks.

- [ ] **Step 1: Write failing static-site contract tests**

Create `tests/test_site.py`. Build a two-section in-memory note, call `render_site`,
and assert:

- the output has `<main>`, `<article>`, `<nav data-toc>`, and ten-compatible section markup;
- headings have deterministic IDs;
- images use `loading="lazy"` and paths such as `assets/images/note-001.png`;
- scripts and styles are local (`styles.css`, `app.js`);
- the HTML contains no `http://`, `https://`, `cdn`, or external font URL;
- all required `data-*` hooks are present.

```python
import unittest

from tools.note_converter.model import Block, Note, Section
from tools.note_converter.site import render_site


class SiteTests(unittest.TestCase):
    def test_renders_local_semantic_reader_contract(self):
        note = Note(
            "Spring Notes",
            ("1.问题一",),
            (
                Section(
                    "01-one",
                    "一、One",
                    (
                        Block("paragraph", "1.问题一"),
                        Block("paragraph", "答案"),
                        Block("image", "https://source.invalid/1"),
                    ),
                ),
            ),
        )
        html = render_site(
            note, {"https://source.invalid/1": "assets/images/note-001.png"}
        )

        for token in (
            "<main",
            "<article",
            "data-toc",
            "data-search-input",
            "data-search-count",
            "data-theme-toggle",
            "data-toc-toggle",
            "data-progress",
            "data-back-to-top",
            'loading="lazy"',
            "assets/images/note-001.png",
            "styles.css",
            "app.js",
        ):
            self.assertIn(token, html)
        self.assertNotIn("http://", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("cdn", html.lower())


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the site tests and verify failure**

Run:

```powershell
python -m unittest tests.test_site -v
```

Expected: import failure for `tools.note_converter.site`.

- [ ] **Step 3: Implement semantic HTML rendering**

Create `tools/note_converter/site.py` using only `html.escape` and the document
model. Implement stable IDs by converting:

- section slugs directly to IDs;
- question headings to `q-{original-number}-{sequence}` so duplicated source
  question numbers still have unique IDs.

Render:

- a header with title, search input, and theme button;
- a progress bar with `data-progress`;
- a sidebar navigation with links to every section and question;
- a main article with paragraphs, lists, fenced-equivalent `<pre><code>`,
  and lazy local images;
- a `data-back-to-top` button;
- local links to `styles.css` and `app.js`.

Update `generate.py` to write `site/index.html` from `render_site`.

The core renderer should follow this complete structure:

```python
from html import escape
import re

from .model import Note


def render_site(note: Note, image_paths: dict[str, str]) -> str:
    questions = set(note.questions)
    question_sequence = 0
    toc: list[str] = []
    article: list[str] = []

    for section in note.sections:
        toc.append(
            f'<a class="toc-section" href="#{section.slug}">{escape(section.title)}</a>'
        )
        article.append(
            f'<section class="topic"><h2 id="{section.slug}">'
            f"{escape(section.title)}</h2>"
        )
        question_open = False
        for block in section.blocks:
            if block.kind == "paragraph" and block.text in questions:
                if question_open:
                    article.append("</section>")
                question_sequence += 1
                number = re.match(r"^(\d+)", block.text).group(1)
                question_id = f"q-{number}-{question_sequence}"
                toc.append(
                    f'<a class="toc-question" href="#{question_id}">'
                    f"{escape(block.text)}</a>"
                )
                article.append(
                    f'<section class="question" data-question>'
                    f'<h3 id="{question_id}">{escape(block.text)}</h3>'
                )
                question_open = True
            elif block.kind == "paragraph":
                article.append(f"<p>{escape(block.text)}</p>")
            elif block.kind == "bullet":
                article.append(f"<ul><li>{escape(block.text)}</li></ul>")
            elif block.kind == "code":
                article.append(f"<pre><code>{escape(block.text)}</code></pre>")
            elif block.kind == "image":
                path = escape(image_paths[block.text], quote=True)
                article.append(
                    f'<img src="{path}" alt="Spring 笔记插图" loading="lazy">'
                )
        if question_open:
            article.append("</section>")
        article.append("</section>")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(note.title)}</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <div class="progress"><span data-progress></span></div>
  <header>
    <h1>{escape(note.title)}</h1>
    <label>搜索 <input type="search" data-search-input></label>
    <output data-search-count></output>
    <button type="button" data-toc-toggle aria-expanded="false">目录</button>
    <button type="button" data-theme-toggle>切换深色模式</button>
  </header>
  <div class="layout">
    <nav data-toc aria-label="章节目录">{''.join(toc)}</nav>
    <main><article>{''.join(article)}</article></main>
  </div>
  <button type="button" data-back-to-top hidden>返回顶部</button>
  <script src="app.js"></script>
</body>
</html>
"""
```

- [ ] **Step 4: Implement responsive CSS**

Create `site/styles.css` with:

- system font stack only;
- CSS custom properties for light and dark palettes;
- maximum article width of `860px`;
- sticky desktop sidebar;
- single-column layout below `900px`;
- readable code blocks with horizontal overflow;
- responsive images with `max-width: 100%`;
- visible keyboard focus styles;
- reduced-motion handling through `@media (prefers-reduced-motion: reduce)`.

Use this dependency-free baseline and refine only values needed by browser
verification:

```css
:root {
  color-scheme: light;
  --bg: #f6f7f9;
  --surface: #ffffff;
  --text: #18212f;
  --muted: #637083;
  --accent: #1769aa;
  --border: #dce1e8;
  --code: #f1f3f5;
}

:root[data-theme="dark"] {
  color-scheme: dark;
  --bg: #11151b;
  --surface: #191f28;
  --text: #e8edf3;
  --muted: #a7b1bf;
  --accent: #6cb6ff;
  --border: #303947;
  --code: #0d1117;
}

* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.75 system-ui, -apple-system, "Segoe UI", sans-serif;
}
header {
  padding: 2rem max(1rem, calc((100vw - 1180px) / 2));
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}
header input { width: min(32rem, 100%); }
.progress {
  position: fixed;
  inset: 0 0 auto;
  z-index: 20;
  height: 3px;
}
.progress span { display: block; width: 0; height: 100%; background: var(--accent); }
.layout {
  display: grid;
  grid-template-columns: 280px minmax(0, 860px);
  gap: 2rem;
  width: min(1180px, calc(100% - 2rem));
  margin: 2rem auto;
}
[data-toc] {
  position: sticky;
  top: 1rem;
  align-self: start;
  max-height: calc(100vh - 2rem);
  overflow: auto;
}
[data-toc] a { display: block; padding: .3rem .5rem; color: var(--muted); }
[data-toc] a[aria-current] { color: var(--accent); font-weight: 700; }
.toc-question { padding-left: 1.25rem !important; font-size: .9rem; }
article {
  padding: clamp(1rem, 3vw, 3rem);
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
}
img { display: block; max-width: 100%; height: auto; margin: 1.5rem auto; }
pre { overflow-x: auto; padding: 1rem; background: var(--code); border-radius: 8px; }
button, input { font: inherit; }
:focus-visible { outline: 3px solid var(--accent); outline-offset: 2px; }
[data-back-to-top] { position: fixed; right: 1rem; bottom: 1rem; }
[data-back-to-top][hidden], [data-question][hidden] { display: none; }

@media (max-width: 899px) {
  .layout { display: block; width: min(100% - 1rem, 860px); }
  [data-toc] { display: none; position: static; max-height: 16rem; margin-bottom: 1rem; }
  [data-toc][data-open] { display: block; }
}

@media (prefers-reduced-motion: reduce) {
  html { scroll-behavior: auto; }
  *, *::before, *::after { animation-duration: .01ms !important; }
}
```

- [ ] **Step 5: Implement the reader interactions**

Create `site/app.js` with isolated functions:

```javascript
function normalize(value) {
  return value.toLocaleLowerCase("zh-CN").trim();
}

function applySearch(query) {
  const needle = normalize(query);
  let visible = 0;
  document.querySelectorAll("[data-question]").forEach((question) => {
    const matches = !needle || normalize(question.textContent).includes(needle);
    question.hidden = !matches;
    if (matches) visible += 1;
  });
  document.querySelector("[data-search-count]").textContent =
    needle ? `${visible} 个匹配结果` : "";
}

function updateActiveHeading(entries) {
  const visible = entries
    .filter((entry) => entry.isIntersecting)
    .sort((left, right) => left.boundingClientRect.top - right.boundingClientRect.top);
  if (!visible.length) return;
  const id = visible[0].target.id;
  document.querySelectorAll("[data-toc] a").forEach((link) => {
    link.toggleAttribute("aria-current", link.hash === `#${id}`);
  });
}

function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("spring-notes-theme", theme);
}

function updateProgress() {
  const maximum = document.documentElement.scrollHeight - window.innerHeight;
  const percent = maximum > 0 ? (window.scrollY / maximum) * 100 : 0;
  document.querySelector("[data-progress]").style.width = `${percent}%`;
}

const searchInput = document.querySelector("[data-search-input]");
const themeButton = document.querySelector("[data-theme-toggle]");
const tocButton = document.querySelector("[data-toc-toggle]");
const toc = document.querySelector("[data-toc]");
const backToTop = document.querySelector("[data-back-to-top]");
const savedTheme = localStorage.getItem("spring-notes-theme");
const preferredTheme = matchMedia("(prefers-color-scheme: dark)").matches
  ? "dark"
  : "light";
setTheme(savedTheme || preferredTheme);

searchInput.addEventListener("input", (event) => applySearch(event.target.value));
themeButton.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  setTheme(next);
});
tocButton.addEventListener("click", () => {
  const open = toc.toggleAttribute("data-open");
  tocButton.setAttribute("aria-expanded", String(open));
});
backToTop.addEventListener("click", () => {
  const behavior = matchMedia("(prefers-reduced-motion: reduce)").matches
    ? "auto"
    : "smooth";
  scrollTo({ top: 0, behavior });
});
addEventListener("scroll", () => {
  updateProgress();
  backToTop.hidden = scrollY < 600;
}, { passive: true });

const observer = new IntersectionObserver(updateActiveHeading, {
  rootMargin: "-10% 0px -75% 0px",
});
document.querySelectorAll("article h2, article h3").forEach(
  (heading) => observer.observe(heading)
);
updateProgress();
```

Required behavior:

- search filters question sections and reports the visible match count;
- clearing search restores all content;
- `IntersectionObserver` updates the active TOC link;
- theme respects saved choice, then `prefers-color-scheme`;
- progress bar updates on passive scroll;
- back-to-top becomes visible after 600px and uses smooth scrolling unless reduced motion is requested;
- the page remains fully readable if JavaScript is disabled.

- [ ] **Step 6: Run tests and regenerate the real site**

Run:

```powershell
python -m unittest tests.test_site -v
python -m tools.note_converter.generate `
  --snapshot '..\youdao_note_snapshot.txt' `
  --image-cache '..\youdao_images' `
  --repo-root '.'
```

Expected: tests pass and `site/index.html` is regenerated.

- [ ] **Step 7: Commit the enhanced reader**

Run:

```powershell
git add tools/note_converter/site.py tools/note_converter/generate.py `
  tests/test_site.py site
git commit -m "feat: add enhanced Spring notes reader"
```

---

### Task 5: Add Generated-Content Validation and Pages Deployment

**Files:**
- Create: `tools/validate_generated.py`
- Create: `tests/test_validation.py`
- Create: `.github/workflows/pages.yml`
- Create: `.gitignore`

**Interfaces:**
- Produces: `validate(repo_root: Path) -> list[str]`, returning an empty list on success.
- CLI exits `0` when validation succeeds and `1` after printing every error.
- Workflow packages `_site/` containing `site/*` plus `assets/images/*`.

- [ ] **Step 1: Write failing validation tests**

Create `tests/test_validation.py` with temporary repository fixtures. Test that
`validate` reports:

- a missing chapter;
- a broken Markdown relative link;
- a missing image;
- a remote Youdao image URL;
- a manifest question-count or hash mismatch;
- success for a minimal complete fixture.

```python
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
        "![图](../assets/images/note-001.png)\n",
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
```

- [ ] **Step 2: Run validation tests and verify failure**

Run:

```powershell
python -m unittest tests.test_validation -v
```

Expected: import failure for `tools.validate_generated`.

- [ ] **Step 3: Implement the validator**

In `tools/validate_generated.py`:

```python
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import unquote

MARKDOWN_LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")
QUESTION_HEADING = re.compile(r"^## (.+)$", re.MULTILINE)


def validate(repo_root: Path) -> list[str]:
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
                errors.append(
                    f"broken link in {markdown_path.name}: {raw_target}"
                )

    site_dir = repo_root / "site"
    for site_path in site_dir.glob("*"):
        if not site_path.is_file():
            continue
        text = site_path.read_text("utf-8")
        remote_asset = re.search(
            r'(?:src|href)=["\']https?://|url\(\s*["\']?https?://', text
        )
        if "share.note.youdao.com" in text or remote_asset:
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
```

Use `hashlib.sha256("\n".join(question_titles).encode()).hexdigest()` for the
question-title integrity check. Resolve relative Markdown links against the
document containing each link. Ignore URL fragments after verifying the file
portion exists. Scan `README.md`, generated chapter Markdown, and `site/` for
forbidden runtime references to:

- `share.note.youdao.com`;
- `<script src="http`;
- `<link href="http`;
- CSS `url(http`.

The CLI prints `PASS: generated content is internally consistent` only when
the returned error list is empty.

- [ ] **Step 4: Run validator tests and the real validator**

Run:

```powershell
python -m unittest tests.test_validation -v
python tools/validate_generated.py .
```

Expected: all tests pass and the validator prints the PASS line.

- [ ] **Step 5: Create the Pages workflow**

Create `.gitignore`:

```gitignore
_site/
```

Create `.github/workflows/pages.yml`:

```yaml
name: Deploy Spring notes to Pages

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: true

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.12"
      - run: python -m pip install -r requirements-dev.txt
      - run: python -m unittest discover -s tests -v
      - run: python tools/validate_generated.py .

  build:
    if: github.event_name != 'pull_request'
    needs: validate
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/configure-pages@v5
      - name: Assemble static site
        shell: bash
        run: |
          mkdir -p _site/assets
          cp -R site/. _site/
          cp -R assets/images _site/assets/images
      - uses: actions/upload-pages-artifact@v4
        with:
          path: _site

  deploy:
    if: github.event_name != 'pull_request'
    needs: build
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - name: Deploy
        id: deployment
        uses: actions/deploy-pages@v4
```

These action versions match the current GitHub Pages documentation:
`checkout@v6`, `configure-pages@v5`, `upload-pages-artifact@v4`, and
`deploy-pages@v4`.

- [ ] **Step 6: Commit validation and deployment**

Run:

```powershell
python -m unittest discover -s tests -v
python tools/validate_generated.py .
git diff --check
git add tools/validate_generated.py tests/test_validation.py `
  .gitignore .github/workflows/pages.yml
git commit -m "ci: validate and deploy Spring notes"
```

Expected: all tests pass, validator passes, and commit succeeds.

---

### Task 6: Verify the Complete Reading Experience

**Files:**
- Verify only; modify the smallest responsible file if a check fails.

**Interfaces:**
- Consumes all generated files and tests.
- Produces fresh evidence that Markdown and the enhanced reader meet the design.

- [ ] **Step 1: Run the complete automated suite**

Run:

```powershell
python -m unittest discover -s tests -v
python tools/validate_generated.py .
git diff --check
git status --short
```

Expected:

- all unit tests pass;
- validator prints its PASS line;
- `git diff --check` prints nothing;
- working tree is clean.

- [ ] **Step 2: Verify generated counts independently**

Run:

```powershell
$chapters = Get-ChildItem docs -Filter '*.md' |
  Where-Object Name -Match '^\d{2}-'
$images = Get-ChildItem assets/images -File
$remote = rg -n 'share\.note\.youdao\.com|src="https?://|url\(https?://' `
  README.md docs site
"chapters=$($chapters.Count) images=$($images.Count)"
if ($chapters.Count -ne 10) { throw 'expected 10 chapters' }
if ($images.Count -ne 69) { throw 'expected 69 images' }
if ($LASTEXITCODE -eq 0) { throw 'found forbidden remote runtime asset' }
```

Expected: `chapters=10 images=69` and no forbidden remote runtime asset.

- [ ] **Step 3: Test the static site in a local browser**

Assemble the same directory layout used by Pages and start a hidden local
server from the repository root:

```powershell
New-Item -ItemType Directory -Path '_site\assets' -Force | Out-Null
Copy-Item -Path 'site\*' -Destination '_site' -Recurse -Force
Copy-Item -Path 'assets\images' -Destination '_site\assets' -Recurse -Force
$server = Start-Process python `
  -ArgumentList '-m','http.server','4173','--directory','_site' `
  -WindowStyle Hidden -PassThru
```

Using the browser-control skill, verify at `http://127.0.0.1:4173/`:

- title and all ten section links render;
- an early and late image load successfully;
- searching `循环依赖` produces matches and clearing restores content;
- selecting dark mode changes the page theme and persists after reload;
- scrolling updates the active TOC entry and progress bar;
- the mobile viewport collapses the sidebar without horizontal body overflow;
- the browser console has no errors.

Stop only the specific server process returned by `Start-Process`:

```powershell
Stop-Process -Id $server.Id
```

- [ ] **Step 4: Perform an implementation review and fix any findings**

Review:

- generated Markdown against the source snapshot;
- image placement around at least the first, middle, and last image;
- workflow permissions and action versions;
- no changes under `二、框架源码专题/`;
- no accidental removal of the Word document.

After fixes, repeat Steps 1–3 and commit only if files changed:

```powershell
git add -A
git commit -m "fix: address Spring notes verification findings"
```

---

### Task 7: Push, Merge, Enable Pages, and Verify Production

**Files:**
- No new local files expected.

**Interfaces:**
- Consumes the clean `codex/github-readable-notes` branch.
- Produces the GitHub repository reading experience and optional Pages deployment.

- [ ] **Step 1: Push the feature branch**

Run:

```powershell
git push -u origin codex/github-readable-notes
```

Expected: GitHub reports the branch was created and prints a Pull Request URL.

- [ ] **Step 2: Create the Pull Request**

Create a Pull Request from `codex/github-readable-notes` to `main` with:

Title:

```text
Add GitHub-readable Spring notes and Pages reader
```

Body:

```markdown
## Summary
- convert the Youdao note into ten GitHub-rendered Markdown chapters
- localize all 69 images and preserve the downloadable Word document
- add an optional searchable, responsive GitHub Pages reader
- validate chapter, question, image, and link integrity in CI

## Verification
- `python -m unittest discover -s tests -v`
- `python tools/validate_generated.py .`
- local desktop and mobile browser checks
```

- [ ] **Step 3: Review the remote diff and checks**

Verify on GitHub:

- only the intended README, docs, assets, tools, tests, site, and workflow files changed;
- the Word document and `二、框架源码专题/` remain present;
- every Pull Request check succeeds.

Do not merge while any required check is pending or failing.

- [ ] **Step 4: Enable GitHub Actions as the Pages source**

In repository **Settings → Pages → Build and deployment**, set **Source** to
**GitHub Actions** if it is not already selected. Do this before merging so
the first `main` deployment does not fail because Pages is disabled.

- [ ] **Step 5: Merge the Pull Request**

Use squash merge after all checks pass. Confirm the `main` branch repository
homepage renders the new README immediately.

- [ ] **Step 6: Wait for and verify the Pages deployment**

Verify the workflow run named `Deploy Spring notes to Pages` completes with:

- `validate`: success;
- `build`: success;
- `deploy`: success.

Open:

```text
https://15827196717.github.io/study-spring/
```

Confirm the title, images, search, theme, TOC, and mobile layout work.

- [ ] **Step 7: Verify the company-safe primary path**

Open these `github.com` URLs:

```text
https://github.com/15827196717/study-spring
https://github.com/15827196717/study-spring/blob/main/docs/01-spring-framework.md
https://github.com/15827196717/study-spring/blob/main/docs/10-microservices.md
```

Confirm:

- README renders on the repository home page;
- first and last chapters render;
- local images display;
- chapter navigation stays on `github.com`;
- the content remains usable even if the Pages URL is blocked.

- [ ] **Step 8: Roll back a broken production merge**

If the merged README or chapter paths fail production verification, use the
merged Pull Request's **Revert** action to create a revert Pull Request. Merge
that revert after its checks pass, then fix the feature branch and repeat the
production flow. Do not remove the existing Word document or source-study
directory as an emergency workaround.

---

## Final Verification Checklist

- [ ] `python -m unittest discover -s tests -v` passes with zero failures.
- [ ] `python tools/validate_generated.py .` prints PASS.
- [ ] Ten generated chapter files exist.
- [ ] Ninety-seven source question headings match the manifest hash.
- [ ] Sixty-nine local images exist and are referenced.
- [ ] No runtime content depends on Youdao, a CDN, or an external font.
- [ ] Existing source-study materials and Word document are unchanged.
- [ ] Repository README and first/last chapters render on `github.com`.
- [ ] Pages workflow succeeds, or any Pages-only issue is reported without blocking the company-safe Markdown delivery.
