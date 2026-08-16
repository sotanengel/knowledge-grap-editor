from app.models.schemas import EdgeCreate, NodeCreate
from app.services.validation_service import ValidationService


class FakeOntology:
    def get_class(self, class_id: str):
        from app.models.schemas import OntologyClass

        if class_id == "Person":
            return OntologyClass(id="Person", label="Person")
        if class_id == "Organization":
            return OntologyClass(id="Organization", label="Organization")
        if class_id == "Product":
            return OntologyClass(id="Product", label="Product")
        return None

    def get_relationship(self, rel_id: str):
        from app.models.schemas import Relationship

        if rel_id == "worksFor":
            return Relationship(
                id="worksFor",
                label="works for",
                domain=["Person"],
                range=["Organization"],
            )
        return None

    def list_properties(self):
        return []


class FakeGraph:
    def get_node(self, node_id: str):
        from app.models.schemas import Node

        nodes = {
            "p1": Node(id="p1", label="Person1", type="Person"),
            "o1": Node(id="o1", label="Org1", type="Organization"),
            "prod1": Node(id="prod1", label="Product1", type="Product"),
        }
        return nodes.get(node_id)


def test_valid_edge_no_warnings():
    svc = ValidationService(FakeOntology(), FakeGraph())  # type: ignore[arg-type]
    warnings = svc.validate_edge(
        EdgeCreate(id="e1", subject="p1", predicate="worksFor", object="o1")
    )
    assert len(warnings) == 0


def test_domain_violation_warning():
    svc = ValidationService(FakeOntology(), FakeGraph())  # type: ignore[arg-type]
    warnings = svc.validate_edge(
        EdgeCreate(id="e1", subject="prod1", predicate="worksFor", object="o1")
    )
    assert any(w.code == "DOMAIN_VIOLATION" for w in warnings)


def test_invalid_node_type():
    svc = ValidationService(FakeOntology(), FakeGraph())  # type: ignore[arg-type]
    warnings = svc.validate_node(NodeCreate(id="x1", label="Unknown", type="UnknownType"))
    assert any(w.code == "INVALID_NODE_TYPE" for w in warnings)
