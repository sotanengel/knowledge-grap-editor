from dataclasses import dataclass, field

from app.ontology.expressions.class_expression import ClassExpression
from app.ontology.models.enums import PropertyCharacteristic, PropertyType
from app.ontology.models.resource import Resource


@dataclass
class OwlProperty(Resource):
    property_type: PropertyType = PropertyType.DATATYPE
    domain: list[str | ClassExpression] = field(default_factory=list)
    range_iris: list[str | ClassExpression] = field(default_factory=list)
    sub_property_of: list[str] = field(default_factory=list)
    inverse_of: str | None = None
    characteristics: set[PropertyCharacteristic] = field(default_factory=set)
    editor_required: bool = False
