from __future__ import annotations

from app.models.schemas import SuggestResponse, SuggestResult
from app.services.ontology_service import OntologyService


class SuggestService:
    MAX_SCORE = 100.0

    def __init__(self, ontology: OntologyService) -> None:
        self.ontology = ontology

    def _score_class(
        self, query: str, class_id: str, label: str, description: str, aliases: list[str]
    ) -> float:
        q = query.strip().lower()
        if not q:
            return 0.0
        scores: list[float] = []
        lid = class_id.lower()
        ll = label.lower()
        if lid == q or ll == q:
            scores.append(100)
        if lid.startswith(q) or ll.startswith(q):
            scores.append(80)
        if q in lid or q in ll:
            scores.append(60)
        for alias in aliases:
            al = alias.lower()
            if al == q:
                scores.append(90)
            elif q in al or al.startswith(q):
                scores.append(70)
        if description and q in description.lower():
            scores.append(50)
        return max(scores) if scores else 0.0

    def suggest_classes(self, query: str, limit: int = 10) -> SuggestResponse:
        results: list[SuggestResult] = []
        for cls in self.ontology.list_classes():
            score = self._score_class(query, cls.id, cls.label, cls.description, cls.aliases)
            if score > 0:
                results.append(
                    SuggestResult(
                        id=cls.id,
                        label=cls.label,
                        description=cls.description,
                        score=round(score / self.MAX_SCORE, 2),
                        parent_classes=cls.parent_classes,
                        examples=cls.examples,
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return SuggestResponse(results=results[:limit])

    def suggest_relationships(self, query: str, limit: int = 10) -> SuggestResponse:
        results: list[SuggestResult] = []
        for rel in self.ontology.list_relationships():
            score = self._score_class(query, rel.id, rel.label, rel.description, rel.aliases)
            if score > 0:
                results.append(
                    SuggestResult(
                        id=rel.id,
                        label=rel.label,
                        description=rel.description,
                        score=round(score / self.MAX_SCORE, 2),
                    )
                )
        results.sort(key=lambda r: r.score, reverse=True)
        return SuggestResponse(results=results[:limit])

    def find_similar_classes(self, query: str, threshold: float = 0.7) -> SuggestResponse:
        response = self.suggest_classes(query, limit=5)
        filtered = [r for r in response.results if r.score >= threshold]
        return SuggestResponse(results=filtered)
