from app.services.suggest_service import SuggestService


class FakeOntology:
    def list_classes(self):
        from app.models.schemas import OntologyClass

        return [
            OntologyClass(
                id="Organization",
                label="組織",
                labels=["Organization", "組織"],
                description="組織・企業・団体",
                aliases=["会社", "組織", "企業"],
            ),
            OntologyClass(
                id="Product",
                label="製品",
                labels=["Product", "製品"],
                description="製品",
                aliases=["商品", "スマホ"],
            ),
        ]

    def list_relationships(self):
        return []


def test_suggest_exact_alias():
    svc = SuggestService(FakeOntology())  # type: ignore[arg-type]
    result = svc.suggest_classes("会社")
    assert result.results[0].id == "Organization"
    assert result.results[0].score >= 0.85


def test_suggest_japanese_label():
    svc = SuggestService(FakeOntology())  # type: ignore[arg-type]
    result = svc.suggest_classes("組織")
    assert result.results[0].id == "Organization"
    assert result.results[0].score >= 0.9


def test_suggest_smartphone_alias():
    svc = SuggestService(FakeOntology())  # type: ignore[arg-type]
    result = svc.suggest_classes("スマホ")
    assert result.results[0].id == "Product"
    assert result.results[0].score >= 0.85


def test_suggest_partial():
    svc = SuggestService(FakeOntology())  # type: ignore[arg-type]
    result = svc.suggest_classes("Organ")
    assert result.results[0].id == "Organization"


def test_suggest_empty_query_returns_all():
    svc = SuggestService(FakeOntology())  # type: ignore[arg-type]
    result = svc.suggest_classes("")
    assert len(result.results) == 2
    ids = {r.id for r in result.results}
    assert ids == {"Organization", "Product"}
