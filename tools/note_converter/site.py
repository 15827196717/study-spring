"""Render the note model as a self-contained, dependency-free reader page."""

from html import escape
import re

from .model import Note


def _question_id(text: str, sequence: int) -> str:
    """Create a stable unique id while preserving the source question number."""
    match = re.match(r"^(\d+)", text)
    number = match.group(1) if match else "unnumbered"
    return f"q-{number}-{sequence}"


def _table_cell(lines: tuple[str, ...]) -> str:
    return "<br>".join(escape(line) for line in lines)


def render_site(note: Note, image_paths: dict[str, str]) -> str:
    """Render a semantic static reader using only local style and script files."""
    questions = set(note.questions)
    question_sequence = 0
    image_sequence = 0
    toc: list[str] = []
    article: list[str] = []

    for section in note.sections:
        section_id = escape(section.slug, quote=True)
        toc.append(
            f'<a class="toc-section" href="#{section_id}">{escape(section.title)}</a>'
        )
        article.append(
            f'<section class="topic"><h2 id="{section_id}">{escape(section.title)}</h2>'
        )
        question_open = False
        list_open = False
        image_context = section.title

        for block in section.blocks:
            is_list_item = block.kind == "bullet" or (
                block.kind == "link" and block.is_bullet
            )
            if list_open and not is_list_item:
                article.append("</ul>")
                list_open = False

            if block.kind == "paragraph" and block.text in questions:
                if question_open:
                    article.append("</section>")
                question_sequence += 1
                image_context = block.text
                question_id = _question_id(block.text, question_sequence)
                toc.append(
                    f'<a class="toc-question" href="#{question_id}">'
                    f"{escape(block.text)}</a>"
                )
                article.append(
                    '<section class="question" data-question>'
                    f'<h3 id="{question_id}">{escape(block.text)}</h3>'
                )
                question_open = True
            elif block.kind == "paragraph":
                article.append(f"<p>{escape(block.text)}</p>")
            elif block.kind == "bullet":
                if not list_open:
                    article.append("<ul>")
                    list_open = True
                article.append(f"<li>{escape(block.text)}</li>")
            elif block.kind == "code":
                article.append(f"<pre><code>{escape(block.text)}</code></pre>")
            elif block.kind == "link":
                if block.link is None:
                    raise ValueError("link block is missing link data")
                link = (
                    f'<a href="{escape(block.link.url, quote=True)}">'
                    f"{escape(block.link.label)}</a>"
                )
                if block.is_bullet:
                    if not list_open:
                        article.append("<ul>")
                        list_open = True
                    article.append(f"<li>{link}</li>")
                else:
                    article.append(f"<p>{link}</p>")
            elif block.kind == "table":
                if block.table is None:
                    raise ValueError("table block is missing table data")
                if block.table.rows:
                    header, *body = block.table.rows
                    article.append(
                        "<table><thead><tr>"
                        + "".join(
                            f"<th>{_table_cell(cell.lines)}</th>"
                            for cell in header.cells
                        )
                        + "</tr></thead>"
                    )
                    article.append("<tbody>")
                    article.extend(
                        "<tr>"
                        + "".join(
                            f"<td>{_table_cell(cell.lines)}</td>"
                            for cell in row.cells
                        )
                        + "</tr>"
                        for row in body
                    )
                    article.append("</tbody></table>")
            elif block.kind == "image":
                image_sequence += 1
                path = escape(image_paths[block.text], quote=True)
                alt = escape(
                    f"笔记图片 {image_sequence}：{image_context}", quote=True
                )
                article.append(
                    f'<img src="{path}" alt="{alt}" loading="lazy">'
                )

        if list_open:
            article.append("</ul>")
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
  <div class="progress" aria-hidden="true"><span data-progress></span></div>
  <header>
    <h1>{escape(note.title)}</h1>
    <label>搜索 <input type="search" data-search-input></label>
    <output data-search-count aria-live="polite"></output>
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
