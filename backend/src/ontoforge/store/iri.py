"""IRI minting (§6.2).

The user only ever types a label. Instance IRIs are opaque and **immutable** --
renaming a node changes ``rdfs:label``, never the IRI. Ontology terms get a
readable IRI derived from their label, because those are the names people read
in exported Turtle.
"""

from __future__ import annotations

import unicodedata
from typing import Literal as LiteralType

from pyoxigraph import BlankNode, NamedNode
from ulid import ULID

SlugStyle = LiteralType["pascal", "camel"]

ONTOLOGY_SUFFIX = "ont#"
INSTANCE_SUFFIX = "id/"
SKOLEM_SUFFIX = ".well-known/genid/"


def _tokenise(label: str) -> list[str]:
    """Split ``label`` into the alphanumeric runs usable inside an IRI.

    Anything else -- spaces, punctuation, and the characters RFC 3987 forbids --
    acts as a separator. Non-ASCII letters survive: IRIs accept them, so a
    Japanese label needs no transliteration.
    """
    normalised = unicodedata.normalize("NFKC", label)
    tokens: list[str] = []
    current: list[str] = []
    for character in normalised:
        if character.isalnum():
            current.append(character)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return tokens


def _capitalise(token: str) -> str:
    # Keep acronyms intact: "HTTP" must not become "Http".
    if token.isupper() and len(token) > 1:
        return token
    return token[0].upper() + token[1:]


def _uncapitalise(token: str) -> str:
    if token.isupper() and len(token) > 1:
        return token.lower()
    return token[0].lower() + token[1:]


def slugify_term(label: str, *, style: SlugStyle) -> str:
    """Turn ``label`` into an ontology term name, or ``""`` if nothing usable remains."""
    tokens = _tokenise(label)
    if not tokens:
        return ""
    head, *tail = tokens
    first = _capitalise(head) if style == "pascal" else _uncapitalise(head)
    return first + "".join(_capitalise(token) for token in tail)


class IriMinter:
    """Mints the IRIs for one graph space, all hanging off a single base IRI."""

    def __init__(self, base_iri: str) -> None:
        cleaned = base_iri.strip()
        if not cleaned:
            raise ValueError("base_iri must not be empty")
        self.base_iri = cleaned if cleaned.endswith(("/", "#")) else f"{cleaned}/"

    @property
    def ontology_namespace(self) -> str:
        return f"{self.base_iri}{ONTOLOGY_SUFFIX}"

    @property
    def instance_namespace(self) -> str:
        return f"{self.base_iri}{INSTANCE_SUFFIX}"

    def new_instance(self) -> NamedNode:
        """A fresh, opaque, permanent IRI for an instance."""
        return NamedNode(f"{self.instance_namespace}{ULID()}")

    def class_iri(self, label: str) -> NamedNode:
        return NamedNode(f"{self.ontology_namespace}{self._term(label, style='pascal')}")

    def property_iri(self, label: str) -> NamedNode:
        return NamedNode(f"{self.ontology_namespace}{self._term(label, style='camel')}")

    def term_iri(self, name: str) -> NamedNode:
        """An ontology term IRI from an already-slugged ``name``."""
        return NamedNode(f"{self.ontology_namespace}{name}")

    def skolemize(self, blank: BlankNode) -> NamedNode:
        """Replace a blank node with a stable IRI (§4.3)."""
        return NamedNode(f"{self.base_iri}{SKOLEM_SUFFIX}{blank.value}")

    def is_instance(self, iri: NamedNode) -> bool:
        return iri.value.startswith(self.instance_namespace)

    def _term(self, label: str, *, style: SlugStyle) -> str:
        slug = slugify_term(label, style=style)
        if slug:
            return slug
        # Nothing survived: fall back to a generated but still readable name.
        fallback = "Term" if style == "pascal" else "term"
        return f"{fallback}{ULID()}"
