from dataclasses import dataclass


@dataclass
class LiteralValue:
    lexical: str
    datatype: str | None = None
    language: str | None = None
