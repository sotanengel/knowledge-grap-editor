from dataclasses import dataclass
from enum import StrEnum


class TripleSource(StrEnum):
    EXPLICIT = "explicit"
    INFERRED = "inferred"


class TripleCategory(StrEnum):
    TBOX = "tbox"
    ABOX = "abox"
    ANNOTATION = "annotation"


@dataclass
class Triple:
    subject: str
    predicate: str
    object: str
    object_is_literal: bool = False
    literal_datatype: str | None = None
    literal_language: str | None = None
    source: TripleSource = TripleSource.EXPLICIT
    category: TripleCategory = TripleCategory.TBOX

    @property
    def is_annotation(self) -> bool:
        return self.category == TripleCategory.ANNOTATION

    @property
    def is_inferred(self) -> bool:
        return self.source == TripleSource.INFERRED
