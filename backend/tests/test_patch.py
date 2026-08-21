from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.changelog.patch import Patch, PatchParseError, parse_patches, serialize_patch
from ontoforge.store import graphs

ALICE = NamedNode("https://example.org/kg/id/alice")
LABEL = NamedNode("http://www.w3.org/2000/01/rdf-schema#label")
NAME = Literal("田中太郎", language="ja")


def _patch(**kwargs: object) -> Patch:
    defaults: dict[str, object] = {
        "seq": 1,
        "actor": "user",
        "additions": [Quad(ALICE, LABEL, NAME, graphs.DATA)],
        "deletions": [],
    }
    defaults.update(kwargs)
    return Patch.create(**defaults)  # type: ignore[arg-type]


def test_a_patch_carries_a_sequence_an_actor_and_a_timestamp() -> None:
    patch = _patch()
    assert patch.seq == 1
    assert patch.actor == "user"
    assert patch.id
    assert patch.timestamp.tzinfo is not None


def test_serialisation_uses_rdf_patch_a_and_d_lines() -> None:
    text = serialize_patch(_patch(deletions=[Quad(ALICE, LABEL, Literal("old"), graphs.DATA)]))
    assert "TX ." in text
    assert "TC ." in text
    assert text.count("\nA ") == 1
    assert text.count("\nD ") == 1
    assert 'H actor "user" .' in text


def test_round_trip_through_the_serialiser() -> None:
    original = _patch(
        seq=7,
        actor="import:people.csv",
        deletions=[Quad(ALICE, LABEL, Literal("old"), graphs.DATA)],
    )
    (restored,) = parse_patches(serialize_patch(original))
    assert restored.seq == original.seq
    assert restored.actor == original.actor
    assert restored.id == original.id
    assert restored.additions == original.additions
    assert restored.deletions == original.deletions


def test_several_patches_parse_from_one_append_only_stream() -> None:
    stream = "".join(serialize_patch(_patch(seq=n)) for n in range(1, 4))
    assert [patch.seq for patch in parse_patches(stream)] == [1, 2, 3]


def test_inverting_a_patch_swaps_additions_and_deletions() -> None:
    patch = _patch(deletions=[Quad(ALICE, LABEL, Literal("old"), graphs.DATA)])
    inverse = patch.invert(seq=2)
    assert inverse.additions == patch.deletions
    assert inverse.deletions == patch.additions
    assert inverse.seq == 2
    assert inverse.inverse_of == patch.id


def test_an_empty_patch_is_reported_as_such() -> None:
    assert _patch(additions=[]).is_empty
    assert not _patch().is_empty


def test_quads_in_the_default_graph_round_trip() -> None:
    patch = Patch.create(seq=1, actor="user", additions=[Quad(ALICE, LABEL, NAME)], deletions=[])
    (restored,) = parse_patches(serialize_patch(patch))
    assert restored.additions == patch.additions


def test_a_quad_carrying_an_rdf_12_triple_term_round_trips() -> None:
    from pyoxigraph import Triple

    from ontoforge.namespaces import RDF_REIFIES

    reifier = NamedNode("urn:ontoforge:derivation/1")
    edge = Triple(ALICE, LABEL, NAME)
    patch = Patch.create(
        seq=1, actor="reasoner", additions=[Quad(reifier, RDF_REIFIES, edge, graphs.INFERRED)]
    )
    (restored,) = parse_patches(serialize_patch(patch))
    assert restored.additions == patch.additions


def test_an_unterminated_transaction_is_rejected() -> None:
    with pytest.raises(PatchParseError, match="TC"):
        parse_patches("TX .\nA <http://a> <http://b> <http://c> .\n")


def test_an_unknown_operation_line_is_rejected() -> None:
    with pytest.raises(PatchParseError, match="operation"):
        parse_patches("TX .\nX <http://a> <http://b> <http://c> .\nTC .\n")


def test_a_row_outside_a_transaction_is_rejected() -> None:
    with pytest.raises(PatchParseError, match="transaction"):
        parse_patches("A <http://a> <http://b> <http://c> .\n")
