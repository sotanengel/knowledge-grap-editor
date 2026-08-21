from __future__ import annotations

import pytest
from pyoxigraph import Literal, NamedNode, Quad

from ontoforge.literals import XSD_DATE, XSD_STRING
from ontoforge.namespaces import RDF_TYPE, RDFS_LABEL
from ontoforge.runtime import Runtime
from ontoforge.store import graphs
from ontoforge.validation.service import ValidationService
from ontoforge.validation.shapes import PropertyConstraint, ShapeSpec

ONT = "https://example.org/kg/ont#"
ID = "https://example.org/kg/id/"

PERSON = NamedNode(f"{ONT}Person")
ORGANIZATION = NamedNode(f"{ONT}Organization")
BIRTH_DATE = NamedNode(f"{ONT}birthDate")
WORKS_FOR = NamedNode(f"{ONT}worksFor")
ALICE = NamedNode(f"{ID}alice")
ACME = NamedNode(f"{ID}acme")

REQUIRE_BIRTH_DATE = ShapeSpec(
    name="person",
    target_class=PERSON.value,
    label="人物",
    properties=[
        PropertyConstraint(
            path=BIRTH_DATE.value,
            min_count=1,
            max_count=1,
            datatype=XSD_DATE.value,
            message="人物には生年月日が必要です",
        )
    ],
)


@pytest.fixture
def service(runtime: Runtime) -> ValidationService:
    runtime.write(
        additions=[
            Quad(ALICE, RDF_TYPE, PERSON, graphs.DATA),
            Quad(ALICE, RDFS_LABEL, Literal("田中太郎", language="ja"), graphs.DATA),
        ]
    )
    return ValidationService(runtime)


# ---------------------------------------------------------------- shapes


def test_a_form_becomes_shacl_in_the_shapes_graph(
    service: ValidationService, runtime: Runtime
) -> None:
    saved = service.save_shape(REQUIRE_BIRTH_DATE)
    assert saved["@id"] == "https://example.org/kg/shape/person"
    assert runtime.store.count(graphs.SHAPES) == saved["quads"]
    assert runtime.store.count(graphs.DATA) == 2


def test_saving_the_same_shape_twice_replaces_it(
    service: ValidationService, runtime: Runtime
) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    first = runtime.store.count(graphs.SHAPES)
    service.save_shape(REQUIRE_BIRTH_DATE)
    assert runtime.store.count(graphs.SHAPES) == first


def test_a_shape_can_be_deleted(service: ValidationService, runtime: Runtime) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    assert service.delete_shape("person") > 0
    assert runtime.store.count(graphs.SHAPES) == 0


# ---------------------------------------------------------------- validation


def test_with_no_shapes_everything_conforms(service: ValidationService) -> None:
    report = service.validate()
    assert report.conforms
    assert report.shapes == 0


def test_a_missing_required_property_is_reported(service: ValidationService) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    report = service.validate()
    assert not report.conforms
    assert [finding.constraint for finding in report.findings] == ["MinCountConstraintComponent"]


def test_a_finding_names_the_node_by_its_label_not_its_iri(service: ValidationService) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    (finding,) = service.validate().findings
    assert finding.focus_node == ALICE.value
    assert finding.focus_label == "田中太郎"


def test_a_finding_carries_a_repair_the_user_can_act_on(service: ValidationService) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    (finding,) = service.validate().findings
    assert "田中太郎" in finding.suggestion
    assert "birthDate" in finding.suggestion


def test_supplying_the_missing_value_makes_it_conform(
    service: ValidationService, runtime: Runtime
) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    runtime.write(
        additions=[Quad(ALICE, BIRTH_DATE, Literal("1990-04-01", datatype=XSD_DATE), graphs.DATA)]
    )
    assert service.validate().conforms


def test_the_wrong_datatype_is_reported(service: ValidationService, runtime: Runtime) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    runtime.write(
        additions=[Quad(ALICE, BIRTH_DATE, Literal("昨日", datatype=XSD_STRING), graphs.DATA)]
    )
    constraints = {finding.constraint for finding in service.validate().findings}
    assert "DatatypeConstraintComponent" in constraints


def test_a_class_constraint_reports_the_wrong_kind_of_target(
    service: ValidationService, runtime: Runtime
) -> None:
    service.save_shape(
        ShapeSpec(
            name="employment",
            target_class=PERSON.value,
            properties=[PropertyConstraint(path=WORKS_FOR.value, **{"class": ORGANIZATION.value})],
        )
    )
    runtime.write(
        additions=[
            Quad(ALICE, WORKS_FOR, ACME, graphs.DATA),
            Quad(ACME, RDFS_LABEL, Literal("株式会社アクメ", language="ja"), graphs.DATA),
        ]
    )
    report = service.validate()
    assert not report.conforms
    (finding,) = [f for f in report.findings if f.constraint == "ClassConstraintComponent"]
    assert "株式会社アクメ" in finding.suggestion or ACME.value in str(finding.value)


def test_the_report_lists_which_nodes_to_highlight(service: ValidationService) -> None:
    service.save_shape(REQUIRE_BIRTH_DATE)
    assert service.validate().as_dict()["violated"] == [ALICE.value]


def test_a_warning_severity_is_carried_through(service: ValidationService) -> None:
    service.save_shape(
        ShapeSpec(
            name="soft",
            target_class=PERSON.value,
            properties=[PropertyConstraint(path=BIRTH_DATE.value, min_count=1, severity="warning")],
        )
    )
    (finding,) = service.validate().findings
    assert finding.severity == "Warning"


def test_derived_triples_are_taken_into_account(
    service: ValidationService, runtime: Runtime
) -> None:
    # A node typed only by inference must still be validated (§10.1 + §10.2).
    bob = NamedNode(f"{ID}bob")
    runtime.write(additions=[Quad(bob, RDF_TYPE, PERSON, graphs.INFERRED)])
    service.save_shape(REQUIRE_BIRTH_DATE)
    assert bob.value in service.validate().as_dict()["violated"]
