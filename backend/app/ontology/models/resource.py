from dataclasses import dataclass, field


@dataclass
class Annotation:
    property: str
    value: str
    language: str | None = None
    datatype: str | None = None


@dataclass
class Resource:
    iri: str
    types: list[str] = field(default_factory=list)
    annotations: list[Annotation] = field(default_factory=list)
