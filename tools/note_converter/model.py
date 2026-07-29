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
