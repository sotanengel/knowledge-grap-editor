"""The named graphs OntoForge keeps its quads in (§6.1).

Authored content, generated content, imported vocabularies and pure display
state each get their own graph so that they never contaminate one another.
"""

from __future__ import annotations

from pyoxigraph import NamedNode

NAMESPACE = "urn:ontoforge:"

#: Class and property definitions (TBox). Edited by the user.
ONTOLOGY = NamedNode(f"{NAMESPACE}ontology")
#: Instances and facts (ABox). Edited by the user.
DATA = NamedNode(f"{NAMESPACE}data")
#: SHACL shapes. Edited by the user.
SHAPES = NamedNode(f"{NAMESPACE}shapes")
#: Triples produced by the reasoner. Regenerated, never hand-edited.
INFERRED = NamedNode(f"{NAMESPACE}inferred")
#: Node coordinates and other display state, kept out of the RDF proper.
LAYOUT = NamedNode(f"{NAMESPACE}layout")

VOCAB_PREFIX = f"{NAMESPACE}vocab/"

#: Graphs the user may write to directly.
USER_EDITABLE = frozenset({ONTOLOGY, DATA, SHAPES})
#: Graphs the system owns.
SYSTEM_OWNED = frozenset({INFERRED, LAYOUT})
#: What an export contains unless the caller asks for more.
DEFAULT_EXPORT = (ONTOLOGY, DATA, SHAPES)


def vocab_graph(name: str) -> NamedNode:
    """Return the read-only graph holding the external vocabulary ``name``."""
    cleaned = name.strip()
    if not cleaned:
        raise ValueError("vocabulary name must not be empty")
    if "/" in cleaned:
        raise ValueError(f"vocabulary name must not contain '/': {name!r}")
    return NamedNode(f"{VOCAB_PREFIX}{cleaned}")


def is_vocab_graph(graph: NamedNode) -> bool:
    """Whether ``graph`` holds an imported external vocabulary."""
    return graph.value.startswith(VOCAB_PREFIX)


def vocab_name(graph: NamedNode) -> str:
    """The vocabulary name behind a vocabulary graph IRI."""
    if not is_vocab_graph(graph):
        raise ValueError(f"{graph.value} is not a vocabulary graph")
    return graph.value.removeprefix(VOCAB_PREFIX)


def is_writable(graph: NamedNode) -> bool:
    """Whether the user interface may write to ``graph``."""
    return graph in USER_EDITABLE
