from __future__ import annotations

import re

from app.models.schemas import SuggestResponse, SuggestResult
from app.services.ontology_service import OntologyService

_JA_RE = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]")


class SuggestService:
    MAX_SCORE = 100.0

    def __init__(self, ontology: OntologyService) -> None:
        self.ontology = ontology

    @staticmethod
    def _has_japanese(text: str) -> bool:
        return bool(_JA_RE.search(text))

    def _score_class(
        self,
        query: str,
        class_id: str,
        label: str,
        labels: list[str],
        description: str,
        aliases: list[str],
        examples: list[str],
    ) -> float:
        q = query.strip().lower()
        if not q:
            return 50.0
        scores: list[float] = []
        lid = class_id.lower()
        searchable_labels = labels or [label]
        if lid == q:
            scores.append(100)
        for lbl in searchable_labels:
            ll = lbl.lower()
            if ll == q:
                scores.append(100)
            if ll.startswith(q):
                scores.append(80)
            if q in ll:
                scores.append(60)
        for alias in aliases:
            al = alias.lower()
            if al == q:
                scores.append(90)
            elif al.startswith(q):
                scores.append(85)
            elif q in al:
                scores.append(70)
        if description and q in description.lower():
            scores.append(55)
        for example in examples:
            if q in example.lower():
                scores.append(55)
        return max(scores) if scores else 0.0

    def suggest_classes(self, query: str, limit: int = 10) -> SuggestResponse:
        q = query.strip()
        results: list[SuggestResult] = []
        for cls in self.ontology.list_classes():
            score = self._score_class(
                q,
                cls.id,
                cls.label,
                cls.labels,
                cls.description,
                cls.aliases,
                cls.examples,
            )
            if score > 0:
                results.append(
                    SuggestResult(
                        id=cls.id,
                        label=cls.label,
                        labels=cls.labels,
                        description=cls.description,
                        score=round(score / self.MAX_SCORE, 2),
                        parent_classes=cls.parent_classes,
                        examples=cls.examples,
                    )
                )
        if not q:
            results.sort(key=lambda r: r.label)
        else:
            results.sort(key=lambda r: r.score, reverse=True)
        return SuggestResponse(results=results[:limit])

    def suggest_relationships(self, query: str, limit: int = 10) -> SuggestResponse:
        q = query.strip()
        results: list[SuggestResult] = []
        for rel in self.ontology.list_relationships():
            score = self._score_class(
                q, rel.id, rel.label, [rel.label], rel.description, rel.aliases, []
            )
            if score > 0:
                results.append(
                    SuggestResult(
                        id=rel.id,
                        label=rel.label,
                        description=rel.description,
                        score=round(score / self.MAX_SCORE, 2),
                    )
                )
        if not q:
            results.sort(key=lambda r: r.label)
        else:
            results.sort(key=lambda r: r.score, reverse=True)
        return SuggestResponse(results=results[:limit])

    def find_similar_classes(self, query: str, threshold: float = 0.7) -> SuggestResponse:
        response = self.suggest_classes(query, limit=5)
        filtered = [r for r in response.results if r.score >= threshold]
        return SuggestResponse(results=filtered)
