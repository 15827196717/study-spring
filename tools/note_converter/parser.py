import json
import re

from .model import Block, Note, Section

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


def parse_snapshot(snapshot: str) -> Note:
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
    source_toc_sections = {
        _decode(match.group(1)).strip()
        for line in lines[starts[0] : starts[1]]
        if (match := re.match(r"^  - generic:\s?(.*)$", line))
        and _decode(match.group(1)).strip() in section_slugs
    }

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

    for line in body:
        code_match = re.match(r"^\s+- code(?::\s?(.*))?$", line)
        if code_match:
            raw = code_match.group(1)
            code_tokens.append(_decode(raw) if raw is not None else "")
            continue
        flush_code()

        image_match = re.match(r'^\s+- img "([^"]+)"$', line)
        if image_match:
            require_section()
            current_blocks.append(Block("image", image_match.group(1)))
            continue

        text_match = re.match(r"^(\s+)- (?:generic|paragraph):\s?(.*)$", line)
        if not text_match:
            continue
        indent, raw = text_match.groups()
        text = _decode(raw).strip()
        if text in section_slugs:
            flush_section()
            current_title = text
        elif text:
            require_section()
            kind = "bullet" if len(indent) >= 4 else "paragraph"
            current_blocks.append(Block(kind, text))

    flush_code()
    flush_section()
    is_full_snapshot = len(source_toc_sections) > 2 or len(questions) > 2
    if is_full_snapshot and len(sections) != len(SECTION_FILES):
        raise ValueError(
            f"expected exactly ten real sections, got {len(sections)}"
        )
    return Note(title, questions, tuple(sections))


def question_titles(note: Note) -> list[str]:
    return list(note.questions)
