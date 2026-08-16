from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RestrictionKind(StrEnum):
    SOME = "someValuesFrom"
    ALL = "allValuesFrom"
    HAS_VALUE = "hasValue"
    HAS_SELF = "hasSelf"
    CARDINALITY = "cardinality"
    MIN = "minCardinality"
    MAX = "maxCardinality"


@dataclass
class ClassExpression(ABC):
    @property
    @abstractmethod
    def kind(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ClassExpression:
        kind = data.get("kind")
        if kind == "named":
            return NamedClassExpression.from_dict(data)
        if kind == "intersection":
            return IntersectionExpression.from_dict(data)
        if kind == "union":
            return UnionExpression.from_dict(data)
        if kind == "complement":
            return ComplementExpression.from_dict(data)
        if kind == "oneOf":
            return OneOfExpression.from_dict(data)
        if kind == "restriction":
            return RestrictionExpression.from_dict(data)
        raise ValueError(f"Unknown ClassExpression kind: {kind}")


@dataclass
class NamedClassExpression(ClassExpression):
    iri: str

    @property
    def kind(self) -> str:
        return "named"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "iri": self.iri}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NamedClassExpression:
        return cls(iri=data["iri"])


@dataclass
class IntersectionExpression(ClassExpression):
    operands: list[ClassExpression] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "intersection"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "operands": [o.to_dict() for o in self.operands]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IntersectionExpression:
        return cls(operands=[ClassExpression.from_dict(o) for o in data.get("operands", [])])


@dataclass
class UnionExpression(ClassExpression):
    operands: list[ClassExpression] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "union"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "operands": [o.to_dict() for o in self.operands]}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UnionExpression:
        return cls(operands=[ClassExpression.from_dict(o) for o in data.get("operands", [])])


@dataclass
class ComplementExpression(ClassExpression):
    operand: ClassExpression | None = None

    @property
    def kind(self) -> str:
        return "complement"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "operand": self.operand.to_dict() if self.operand else None}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ComplementExpression:
        operand_data = data.get("operand")
        operand = ClassExpression.from_dict(operand_data) if operand_data else None
        return cls(operand=operand)


@dataclass
class OneOfExpression(ClassExpression):
    individuals: list[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        return "oneOf"

    def to_dict(self) -> dict[str, Any]:
        return {"kind": self.kind, "individuals": self.individuals}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OneOfExpression:
        return cls(individuals=list(data.get("individuals", [])))


@dataclass
class RestrictionExpression(ClassExpression):
    on_property: str
    restriction_kind: RestrictionKind = RestrictionKind.SOME
    filler: ClassExpression | str | None = None
    cardinality: int | None = None

    @property
    def kind(self) -> str:
        return "restriction"

    def to_dict(self) -> dict[str, Any]:
        filler: dict[str, Any] | str | None
        if isinstance(self.filler, ClassExpression):
            filler = self.filler.to_dict()
        else:
            filler = self.filler
        return {
            "kind": self.kind,
            "on_property": self.on_property,
            "restriction_kind": self.restriction_kind.value,
            "filler": filler,
            "cardinality": self.cardinality,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RestrictionExpression:
        filler_data = data.get("filler")
        filler: ClassExpression | str | None
        if isinstance(filler_data, dict):
            filler = ClassExpression.from_dict(filler_data)
        else:
            filler = filler_data
        return cls(
            on_property=data["on_property"],
            restriction_kind=RestrictionKind(data["restriction_kind"]),
            filler=filler,
            cardinality=data.get("cardinality"),
        )
