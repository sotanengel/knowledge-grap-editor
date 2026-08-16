from dataclasses import dataclass, field

from app.ontology.expressions.class_expression import ClassExpression
from app.ontology.models.literal import LiteralValue
from app.ontology.models.resource import Resource


@dataclass
class Individual(Resource):
    types: list[str | ClassExpression] = field(default_factory=list)
    object_assertions: list[tuple[str, str]] = field(default_factory=list)
    datatype_assertions: list[tuple[str, LiteralValue]] = field(default_factory=list)
    same_as: list[str] = field(default_factory=list)
    different_from: list[str] = field(default_factory=list)
