from __future__ import annotations

import pytest
from pyoxigraph import NamedNode

from ontoforge.store import graphs


def test_named_graphs_match_the_specification() -> None:
    assert NamedNode("urn:ontoforge:ontology") == graphs.ONTOLOGY
    assert NamedNode("urn:ontoforge:data") == graphs.DATA
    assert NamedNode("urn:ontoforge:shapes") == graphs.SHAPES
    assert NamedNode("urn:ontoforge:inferred") == graphs.INFERRED
    assert NamedNode("urn:ontoforge:layout") == graphs.LAYOUT


def test_vocabulary_graphs_are_namespaced_per_vocabulary() -> None:
    assert graphs.vocab_graph("schema.org") == NamedNode("urn:ontoforge:vocab/schema.org")


def test_vocabulary_graph_rejects_an_empty_name() -> None:
    with pytest.raises(ValueError, match="name"):
        graphs.vocab_graph("")


def test_user_editable_graphs_exclude_generated_ones() -> None:
    assert graphs.ONTOLOGY in graphs.USER_EDITABLE
    assert graphs.DATA in graphs.USER_EDITABLE
    assert graphs.SHAPES in graphs.USER_EDITABLE
    assert graphs.INFERRED not in graphs.USER_EDITABLE
    assert graphs.LAYOUT not in graphs.USER_EDITABLE


def test_is_vocab_graph_recognises_vocabulary_graphs() -> None:
    assert graphs.is_vocab_graph(graphs.vocab_graph("skos"))
    assert not graphs.is_vocab_graph(graphs.DATA)


def test_exportable_graphs_default_to_the_authored_content() -> None:
    assert graphs.DEFAULT_EXPORT == (graphs.ONTOLOGY, graphs.DATA, graphs.SHAPES)
