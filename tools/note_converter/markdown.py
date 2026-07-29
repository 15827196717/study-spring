from html import escape

from .model import Note


def _markdown_text(text: str) -> str:
    return escape(text, quote=False)


def _markdown_label(text: str) -> str:
    return _markdown_text(text).replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _table_cell(lines: tuple[str, ...]) -> str:
    return "<br>".join(
        _markdown_text(line).replace("\\", "\\\\").replace("|", "\\|")
        for line in lines
    )


def render_chapters(note: Note, image_paths: dict[str, str]) -> dict[str, str]:
    """Render each note section as a repository-relative Markdown chapter."""
    questions = set(note.questions)
    rendered: dict[str, str] = {}
    image_number = 0

    for index, section in enumerate(note.sections):
        lines = [f"# {section.title}", "", "[返回首页](../README.md)", ""]
        image_context = section.title
        for block in section.blocks:
            if block.kind == "paragraph" and block.text in questions:
                image_context = block.text
                lines.extend((f"## {_markdown_text(block.text)}", ""))
            elif block.kind == "paragraph":
                lines.extend((_markdown_text(block.text), ""))
            elif block.kind == "bullet":
                lines.extend((f"- {_markdown_text(block.text)}", ""))
            elif block.kind == "code":
                lines.extend(("```", block.text, "```", ""))
            elif block.kind == "link":
                if block.link is None:
                    raise ValueError("link block is missing link data")
                prefix = "- " if block.is_bullet else ""
                lines.extend(
                    (
                        f"{prefix}[{_markdown_label(block.link.label)}]"
                        f"({block.link.url})",
                        "",
                    )
                )
            elif block.kind == "table":
                if block.table is None:
                    raise ValueError("table block is missing table data")
                if block.table.rows:
                    header, *body = block.table.rows
                    lines.append(
                        "| " + " | ".join(_table_cell(cell.lines) for cell in header.cells) + " |"
                    )
                    lines.append("| " + " | ".join("---" for _ in header.cells) + " |")
                    lines.extend(
                        "| "
                        + " | ".join(_table_cell(cell.lines) for cell in row.cells)
                        + " |"
                        for row in body
                    )
                    lines.append("")
            elif block.kind == "image":
                image_number += 1
                path = image_paths[block.text]
                alt = _markdown_label(
                    f"笔记图片 {image_number}：{image_context}"
                )
                lines.extend((f"![{alt}](../{path})", ""))

        previous_link = (
            f"[上一章]({note.sections[index - 1].slug}.md)" if index else ""
        )
        next_link = (
            f"[下一章]({note.sections[index + 1].slug}.md)"
            if index + 1 < len(note.sections)
            else ""
        )
        navigation = " · ".join(
            link
            for link in (previous_link, "[返回首页](../README.md)", next_link)
            if link
        )
        lines.extend((navigation, ""))
        rendered[f"docs/{section.slug}.md"] = "\n".join(lines)

    return rendered


def render_readme(note: Note) -> str:
    """Render the repository's GitHub-facing table of contents."""
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
    lines.extend(
        (
            "",
            "## 其他资料",
            "",
            "- [Spring 框架源码专题](二、框架源码专题)",
            "- [下载 Word 版本](最新Spring全家桶面试题—图灵徐庶.docx)",
            "- [增强版网页](https://15827196717.github.io/study-spring/)",
            "",
        )
    )
    return "\n".join(lines)
