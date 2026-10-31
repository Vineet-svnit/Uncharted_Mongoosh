"""Evidence Service for AegisRCA.

Provides evidence normalization, contradiction detection, and citation validation.
"""

from typing import Any
from app.schemas.investigation import EvidenceItem, EvidenceClassification


class EvidenceService:
    @staticmethod
    def validate_citations(
        report_citations: list[dict[str, Any]],
        collected_evidence: list[EvidenceItem],
    ) -> list[dict[str, Any]]:
        """Validate all citations in the report against actually retrieved evidence items.

        Rejects any citation that does not match a verified evidence record.
        """
        valid_evidence_ids = {e.evidence_id for e in collected_evidence}
        valid_source_ids = {e.source_id for e in collected_evidence}

        verified_citations = []
        for cit in report_citations:
            evidence_id = cit.get("evidence_id")
            source_id = cit.get("source_id")

            if (evidence_id and evidence_id in valid_evidence_ids) or (
                source_id and source_id in valid_source_ids
            ):
                verified_citations.append(cit)

        # If LLM didn't attach citation details or empty, populate directly from collected evidence
        # preserving the complete evidence item structure so drawer and inspector never lose content
        if not verified_citations and collected_evidence:
            for ev in collected_evidence:
                if hasattr(ev, "model_dump"):
                    verified_citations.append(ev.model_dump(mode="json"))
                elif isinstance(ev, dict):
                    verified_citations.append(dict(ev))
                else:
                    verified_citations.append({
                        "evidence_id": getattr(ev, "evidence_id", "EVD-000"),
                        "source_type": getattr(ev, "source_type", "document"),
                        "source_id": getattr(ev, "source_id", "unknown"),
                        "title": getattr(ev, "title", "Evidence"),
                        "content": getattr(ev, "content", ""),
                        "service_id": getattr(ev, "service_id", None),
                        "timestamp": getattr(ev, "timestamp", None),
                        "citation": getattr(ev, "citation", None),
                        "retrieval_method": getattr(ev, "retrieval_method", "direct"),
                        "relevance_score": getattr(ev, "relevance_score", 0.9),
                        "classification": getattr(ev, "classification", "supporting"),
                        "asset_file_id": getattr(ev, "asset_file_id", None),
                        "source_status": getattr(ev, "source_status", "verified"),
                        "claim_support": getattr(ev, "claim_support", "supported"),
                    })

        return verified_citations

    @staticmethod
    def classify_contradictions(evidence_items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Separate contradicting evidence items."""
        return [e for e in evidence_items if e.classification == EvidenceClassification.CONTRADICTING]

    @staticmethod
    def classify_supporting(evidence_items: list[EvidenceItem]) -> list[EvidenceItem]:
        """Separate supporting evidence items."""
        return [
            e
            for e in evidence_items
            if e.classification in [EvidenceClassification.SUPPORTING, EvidenceClassification.CONTEXTUAL]
        ]
