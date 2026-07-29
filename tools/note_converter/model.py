from dataclasses import dataclass
from typing import Literal

BlockKind = Literal["paragraph", "bullet", "code", "image", "link", "table"]


@dataclass(frozen=True)
class Link:
    label: str
    url: str


@dataclass(frozen=True)
class TableCell:
    lines: tuple[str, ...]


@dataclass(frozen=True)
class TableRow:
    cells: tuple[TableCell, ...]


@dataclass(frozen=True)
class Table:
    rows: tuple[TableRow, ...]


@dataclass(frozen=True)
class Block:
    kind: BlockKind
    text: str = ""
    link: Link | None = None
    table: Table | None = None
    is_bullet: bool = False


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
