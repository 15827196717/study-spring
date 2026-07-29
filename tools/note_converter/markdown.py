from .model import Note


def render_chapters(note: Note, image_paths: dict[str, str]) -> dict[str, str]:
    """Render each note section as a repository-relative Markdown chapter."""
    questions = set(note.questions)
    rendered: dict[str, str] = {}
    image_number = 0

    for index, section in enumerate(note.sections):
        lines = [f"# {section.title}", "", "[返回首页](../README.md)", ""]
        for block in section.blocks:
            if block.kind == "paragraph" and block.text in questions:
                lines.extend((f"## {block.text}", ""))
            elif block.kind == "paragraph":
                lines.extend((block.text, ""))
            elif block.kind == "bullet":
                lines.extend((f"- {block.text}", ""))
            elif block.kind == "code":
                lines.extend(("```", block.text, "```", ""))
            elif block.kind == "image":
                image_number += 1
                path = image_paths[block.text]
                lines.extend((f"![笔记图片 {image_number}](../{path})", ""))

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
