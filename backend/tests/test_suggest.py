from app.services.suggest_service import SuggestService


class FakeOntology:
    def list_classes(self):
        from app.models.schemas import OntologyClass

        return [
            OntologyClass(
                id="Organization",
                label="Organization",
                description="組織・企業・団体",
                aliases=["会社", "組織", "企業"],
            ),
            OntologyClass(
                id="Product",
                label="Product",
                description="製品",
                aliases=["商品"],
            ),
        ]

    def list_relationships(self):
        return []


def test_suggest_exact_alias():
    svc = SuggestService(FakeOntology())  # type: ignore[arg-type]
    result = svc.suggest_classes("会社")
    assert result.results[0].id == "Organization"
    assert result.results[0].score >= 0.9


def test_suggest_partial():
    svc = SuggestService(FakeOntology())  # type: ignore[arg-type]
    result = svc.suggest_classes("Organ")
    assert result.results[0].id == "Organization"
