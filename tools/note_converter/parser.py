import json
import re

from .model import Block, Link, Note, Section, Table, TableCell, TableRow

SECTION_FILES = (
    ("涓€銆丼pring Framework", "01-spring-framework"),
    ("浜屻€丼pring IOC", "02-spring-ioc"),
    ("涓夈€丼pring Beans", "03-spring-beans"),
    ("鍥涖€丼pring娉ㄨВ", "04-spring-annotations"),
    ("浜斻€丼pring AOP", "05-spring-aop"),
    ("鍏€丼pring浜嬪姟", "06-spring-transactions"),
    ("涓冦€丼pring鍏朵粬", "07-spring-other"),
    ("鍏€丼pringMVC", "08-spring-mvc"),
    ("涔濄€丼pring Boot", "09-spring-boot"),
    ("鍗併€佸井鏈嶅姟", "10-microservices"),
)

# The saved accessibility snapshot is valid UTF-8.  The planning artifact
# preserves a mojibake rendering of these same headings, so accept both forms
# while retaining whichever spelling occurred in the source document.
UTF8_SECTION_FILES = (
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


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _subtree_end(lines: list[str], start: int, base_indent: int) -> int:
    index = start + 1
    while index < len(lines):
        line = lines[index]
        if line.strip() and _indent(line) <= base_indent:
            break
        index += 1
    return index


def _link_block(
    lines: list[str], start: int, *, is_bullet: bool = False
) -> tuple[Block, int]:
    line = lines[start].strip()
    label_match = re.match(r'^- link\s+("(?:[^"\\]|\\.)*"):$', line)
    if not label_match:
        raise ValueError(f"malformed link entry: {line}")
    label = _decode(label_match.group(1))
    end = _subtree_end(lines, start, _indent(lines[start]))
    url = ""
    for child in lines[start + 1 : end]:
        url_match = re.match(r"^\s+- /url:\s?(.*)$", child)
        if url_match:
            url = _decode(url_match.group(1))
            break
    if not url:
        raise ValueError(f"link has no URL: {label}")
    return Block("link", link=Link(label, url), is_bullet=is_bullet), end


def _table_block(lines: list[str], start: int) -> tuple[Block, int]:
    end = _subtree_end(lines, start, _indent(lines[start]))
    rows: list[TableRow] = []
    current_cells: list[TableCell] | None = None
    index = start + 1

    while index < end:
        stripped = lines[index].strip()
        indent = _indent(lines[index])
        if indent == 6 and re.match(r"^- '?row\b", stripped):
            if current_cells is not None:
                rows.append(TableRow(tuple(current_cells)))
            current_cells = []
            index += 1
            continue

        if indent == 8 and re.match(r"^- '?cell\b", stripped):
            if current_cells is None:
                raise ValueError("table cell appears before a row")
            cell_end = _subtree_end(lines, index, indent)
            cell_lines = tuple(
                _decode(match.group(1)).strip()
                for child in lines[index + 1 : cell_end]
                if (match := re.match(r"^\s+- generic:\s?(.*)$", child))
            )
            current_cells.append(TableCell(cell_lines))
            index = cell_end
            continue
        index += 1

    if current_cells is not None:
        rows.append(TableRow(tuple(current_cells)))
    return Block("table", table=Table(tuple(rows))), end


def parse_snapshot(snapshot: str, *, require_complete: bool = False) -> Note:
    """Parse the note iframe while retaining its source TOC independently."""
    try:
        frame = snapshot.split("- iframe:\n", 1)[1].split("\n- paragraph:", 1)[0]
    except IndexError as error:
        raise ValueError("expected a single iframe subtree") from error
    lines = frame.splitlines()
    if not lines or "generic:" not in lines[0]:
        raise ValueError("expected note title as the first iframe entry")
    title = _decode(lines[0].split("generic:", 1)[1])

    section_slugs = dict(SECTION_FILES)
    section_slugs.update(UTF8_SECTION_FILES)
    first_heading_titles = {
        SECTION_FILES[0][0],
        UTF8_SECTION_FILES[0][0],
    }
    starts = [
        index
        for index, line in enumerate(lines)
        if line.startswith("  - generic: ")
        and _decode(line.split("generic:", 1)[1]) in first_heading_titles
    ]
    if len(starts) != 2:
        raise ValueError(f"expected two first-section markers, got {len(starts)}")

    questions = tuple(
        _decode(match.group(1))
        for line in lines[starts[0] : starts[1]]
        if (match := re.match(r"^  - generic:\s?(.*)$", line))
        and re.match(r"^\d+[.、銆乚]", _decode(match.group(1)))
    )
    body = lines[starts[1] :]
    source_toc_slugs = [
        section_slugs[text]
        for line in lines[starts[0] : starts[1]]
        if (match := re.match(r"^  - generic:\s?(.*)$", line))
        and (text := _decode(match.group(1)).strip()) in section_slugs
    ]
    sections: list[Section] = []
    current_title: str | None = None
    current_blocks: list[Block] = []
    code_tokens: list[str] = []

    def require_section() -> None:
        if current_title is None:
            raise ValueError("content appears before a detailed section")

    def flush_code() -> None:
        nonlocal code_tokens
        if not code_tokens:
            return
        require_section()
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
                Section(section_slugs[current_title], current_title, tuple(current_blocks))
            )
        current_blocks = []

    index = 0
    while index < len(body):
        line = body[index]
        if _indent(line) != 2:
            index += 1
            continue

        code_match = re.match(r"^  - code(?::\s?(.*))?$", line)
        if code_match:
            raw = code_match.group(1)
            code_tokens.append(_decode(raw) if raw is not None else "")
            index += 1
            continue
        flush_code()

        image_match = re.match(r'^  - img "([^"]+)"$', line)
        if image_match:
            require_section()
            current_blocks.append(Block("image", image_match.group(1)))
            index += 1
            continue

        if re.match(r"^  - link\b", line):
            require_section()
            link, index = _link_block(body, index)
            current_blocks.append(link)
            continue

        if line == "  - table:":
            require_section()
            table, index = _table_block(body, index)
            current_blocks.append(table)
            continue

        if line == "  - list:":
            require_section()
            end = _subtree_end(body, index, 2)
            child_index = index + 1
            while child_index < end:
                child = body[child_index]
                if _indent(child) == 4:
                    bullet_match = re.match(
                        r"^    - (?:generic|paragraph):\s?(.*)$", child
                    )
                    if bullet_match:
                        text = _decode(bullet_match.group(1)).strip()
                        if text:
                            current_blocks.append(Block("bullet", text))
                        child_index += 1
                        continue
                    if re.match(r"^    - link\b", child):
                        link, child_index = _link_block(
                            body, child_index, is_bullet=True
                        )
                        current_blocks.append(link)
                        continue
                child_index += 1
            index = end
            continue

        text_match = re.match(r"^  - (?:generic|paragraph):\s?(.*)$", line)
        if not text_match:
            index += 1
            continue
        raw = text_match.group(1)
        text = _decode(raw).strip()
        if text in section_slugs:
            flush_section()
            current_title = text
        elif text:
            require_section()
            current_blocks.append(Block("paragraph", text))
        index += 1

    flush_code()
    flush_section()
    if require_complete:
        expected_slugs = [slug for _, slug in SECTION_FILES]
        actual_slugs = [section.slug for section in sections]
        if source_toc_slugs != expected_slugs:
            raise ValueError("expected detailed sections in SECTION_FILES order")
        if len(actual_slugs) != len(expected_slugs):
            raise ValueError(
                f"expected exactly ten real sections, got {len(actual_slugs)}"
            )
        if actual_slugs != expected_slugs:
            raise ValueError("expected detailed sections in SECTION_FILES order")
    return Note(title, questions, tuple(sections))


def question_titles(note: Note) -> list[str]:
    return list(note.questions)
