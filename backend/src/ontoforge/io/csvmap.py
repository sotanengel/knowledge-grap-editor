"""CSV / TSV import mapping (FR-13, §11).

The basic shape is "one row is one instance, one named column is the identity
key, every other column is a property". A mapping is data, not code, so it can
be saved and reused the next time the same export lands on the desk.

Re-importing the same keys updates the same nodes instead of duplicating them:
the key is recorded on the node as ``ontf:externalKey``, and the ULID IRI minted
the first time stays put, because instance IRIs never move (§6.2).
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal as LiteralType

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ontoforge.namespaces import ONTF

ONTF_EXTERNAL_KEY = f"{ONTF}externalKey"
MAPPING_SUFFIX = ".json"
_SAFE_NAME = re.compile(r"^[A-Za-z0-9._\-]+$")

ColumnKind = LiteralType["literal", "reference"]


class ColumnMapping(BaseModel):
    """How one CSV column becomes one property."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    column: str
    predicate: str
    kind: ColumnKind = "literal"
    datatype: str | None = None
    language: str | None = None
    #: Skip the cell when it is blank rather than asserting an empty literal.
    skip_empty: bool = True


class CsvMapping(BaseModel):
    """A reusable description of how a table maps onto the graph."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    label_column: str
    key_column: str | None = None
    types: list[str] = Field(default_factory=list)
    columns: list[ColumnMapping] = Field(default_factory=list)
    delimiter: str = ","

    @field_validator("name")
    @classmethod
    def _name_must_be_a_safe_filename(cls, value: str) -> str:
        if not _SAFE_NAME.match(value):
            raise ValueError(f"mapping name {value!r} may only contain letters, digits, . _ -")
        return value

    @field_validator("delimiter")
    @classmethod
    def _delimiter_must_be_one_character(cls, value: str) -> str:
        if len(value) != 1:
            raise ValueError("delimiter must be exactly one character")
        return value

    @property
    def required_columns(self) -> list[str]:
        needed = [self.label_column, *(mapping.column for mapping in self.columns)]
        if self.key_column:
            needed.append(self.key_column)
        return needed

    def check_against(self, header: list[str]) -> None:
        """Fail early if the file does not have the columns the mapping names."""
        missing = [column for column in self.required_columns if column not in header]
        if missing:
            raise ValueError(f"the file has no column(s) named: {', '.join(sorted(set(missing)))}")


class MappingStore:
    """Saved mappings, one JSON file each, under ``/data/mappings``."""

    def __init__(self, directory: Path | str) -> None:
        self.directory = Path(directory)

    def _path(self, name: str) -> Path:
        if not _SAFE_NAME.match(name):
            raise ValueError(f"mapping name {name!r} may only contain letters, digits, . _ -")
        return self.directory / f"{name}{MAPPING_SUFFIX}"

    def save(self, mapping: CsvMapping) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        path = self._path(mapping.name)
        path.write_text(mapping.model_dump_json(indent=2), encoding="utf-8")
        return path

    def load(self, name: str) -> CsvMapping:
        path = self._path(name)
        if not path.is_file():
            raise LookupError(f"no saved mapping named {name!r}")
        return CsvMapping.model_validate(json.loads(path.read_text(encoding="utf-8")))

    def names(self) -> list[str]:
        if not self.directory.is_dir():
            return []
        return sorted(path.stem for path in self.directory.glob(f"*{MAPPING_SUFFIX}"))

    def delete(self, name: str) -> bool:
        path = self._path(name)
        existed = path.is_file()
        path.unlink(missing_ok=True)
        return existed
