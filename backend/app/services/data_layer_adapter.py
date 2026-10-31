"""Data Layer Adapter for AegisRCA.

Centralizes imports from Member 1's data layer (whether located in backend/ or
in a parallel directory) and normalizes disparate collection formats into
structured, validated EvidenceItem objects.
"""

import os
import sys
import uuid
import logging
from typing import Any

# Ensure data_layer is discoverable whether parallel to backend/ or inside backend/
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
parent_dir = os.path.abspath(os.path.join(backend_dir, ".."))
for p in [backend_dir, parent_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

logger = logging.getLogger(__name__)

try:
    from data_layer import (
        get_dependency_chain as dl_get_dependency_chain,
        search_knowledge as dl_search_knowledge,
        query_telemetry as dl_query_telemetry,
        search_messages as dl_search_messages,
        search_sla as dl_search_sla,
        get_deployments as dl_get_deployments,
        get_incident as dl_get_incident,
        list_incidents as dl_list_incidents,
        search_visual_evidence as dl_search_visual_evidence,
        get_visual_asset as dl_get_visual_asset,
    )
    DATA_LAYER_AVAILABLE = True
except ImportError as err:
    logger.warning(
        f"Member 1 data_layer not currently found in path ({err}). "
        "Adapter is configured in pending integration mode."
    )
    DATA_LAYER_AVAILABLE = False

    def dl_get_dependency_chain(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_search_knowledge(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_query_telemetry(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_search_messages(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_search_sla(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_get_deployments(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_get_incident(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_list_incidents(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_search_visual_evidence(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

    def dl_get_visual_asset(*args, **kwargs):
        raise NotImplementedError("Member 1's data_layer is not yet placed in the project.")

from app.schemas.investigation import EvidenceItem, EvidenceClassification


class DataLayerAdapter:
    """Adapts raw retrieval data into standard AegisRCA Evidence items."""

    def __init__(self) -> None:
        self._evidence_counter = 0

    def _next_evd_id(self) -> str:
        self._evidence_counter += 1
        return f"EVD-{self._evidence_counter:03d}"

    def is_available(self) -> bool:
        return DATA_LAYER_AVAILABLE

    def list_known_incidents(
        self, date: str | None = None, status: str | None = None
    ) -> list[dict[str, Any]]:
        return dl_list_incidents(date=date, status=status)

    def get_incident_details(self, incident_id: str) -> dict[str, Any] | None:
        return dl_get_incident(incident_id=incident_id)

    def trace_service_dependencies(
        self,
        service_id: str,
        environment: str = "production",
        topology_version: str = "prod-2026-10-28",
    ) -> dict[str, Any]:
        return dl_get_dependency_chain(
            service_id=service_id,
            environment=environment,
            topology_version=topology_version,
        )

    def find_recent_deployments(
        self,
        service_id: str,
        start: str | None = None,
        end: str | None = None,
    ) -> list[EvidenceItem]:
        raw_deps = dl_get_deployments(service_id=service_id, start=start, end=end)
        items = []
        for dep in raw_deps:
            pr_id = dep.get("pr_id") or dep.get("deployment_id", "DEP-UNKNOWN")
            citation = dep.get("citation") or {
                "file_name": f"deployments_{service_id}.json",
                "line_start": None,
                "line_end": None,
                "page": None,
            }
            content = f"Deployment {dep.get('deployment_id')} (PR {pr_id}, Commit {dep.get('commit_hash')}): {dep.get('description', '')}. Diff summary: {dep.get('diff_summary', 'None')}"
            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="deployment_pr",
                    source_id=pr_id,
                    title=dep.get("title", f"Deployment for {service_id}"),
                    content=content,
                    service_id=dep.get("service_id", service_id),
                    timestamp=dep.get("timestamp"),
                    citation=citation,
                    retrieval_method="direct_query",
                    relevance_score=1.0,
                    classification=EvidenceClassification.SUPPORTING,
                )
            )
        return items

    def search_engineering_knowledge(
        self,
        query: str,
        source_type: str | None = None,
        service_id: str | None = None,
        incident_id: str | None = None,
        customer_id: str | None = None,
        limit: int = 5,
    ) -> list[EvidenceItem]:
        filters: dict[str, Any] = {}
        if source_type:
            filters["source_type"] = source_type
        if service_id:
            filters["service_id"] = service_id
        if incident_id:
            filters["incident_id"] = incident_id
        if customer_id:
            filters["customer_id"] = customer_id

        raw_docs = dl_search_knowledge(query=query, filters=filters, limit=limit)
        items = []
        for doc in raw_docs:
            src_type = doc.get("source_type", "document")
            citation = doc.get("citation") or {
                "file_name": f"{src_type}_{doc.get('knowledge_id', 'unknown')}.md",
                "line_start": None,
                "line_end": None,
                "page": None,
            }
            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type=src_type,
                    source_id=doc.get("knowledge_id", str(uuid.uuid4())[:8]),
                    title=doc.get("title", "Engineering Knowledge Reference"),
                    content=doc.get("content", ""),
                    service_id=doc.get("service_id"),
                    timestamp=doc.get("timestamp"),
                    citation=citation,
                    retrieval_method=doc.get("retrieval_method", "hybrid"),
                    relevance_score=doc.get("relevance_score", 0.85),
                    classification=EvidenceClassification.SUPPORTING,
                )
            )
        return items

    def query_service_telemetry(
        self, service_id: str, start: str, end: str
    ) -> list[EvidenceItem]:
        raw_events = dl_query_telemetry(service_id=service_id, start=start, end=end)
        items = []
        for ev in raw_events:
            ev_id = ev.get("event_id", f"METRIC-{service_id.upper()}-{uuid.uuid4().hex[:4]}")
            timestamp = ev.get("timestamp")
            summary_parts = []
            for k, v in ev.items():
                if k not in ["event_id", "service_id", "timestamp"]:
                    summary_parts.append(f"{k}: {v}")
            content = f"Telemetry snapshot for {service_id} at {timestamp}: " + ", ".join(summary_parts)

            classification = EvidenceClassification.SUPPORTING
            if "ingress_rps" in ev and ev.get("ingress_rps", 0) < 1500:
                classification = EvidenceClassification.CONTRADICTING

            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="telemetry",
                    source_id=ev_id,
                    title=f"Telemetry observation: {service_id}",
                    content=content,
                    service_id=service_id,
                    timestamp=timestamp,
                    citation={
                        "file_name": f"telemetry_{service_id}.timeseries",
                        "line_start": None,
                        "line_end": None,
                        "page": None,
                    },
                    retrieval_method="timeseries_query",
                    relevance_score=0.95,
                    classification=classification,
                )
            )
        return items

    def search_incident_messages(
        self, query: str, incident_id: str | None = None, limit: int = 10
    ) -> list[EvidenceItem]:
        raw_msgs = dl_search_messages(query=query, incident_id=incident_id, limit=limit)
        items = []
        for msg in raw_msgs:
            msg_id = msg.get("message_id", "MSG-SLACK-UNKNOWN")
            channel = msg.get("channel", "#incident-war-room")
            author = msg.get("author", "engineer")
            content = f"[{channel}] {author} at {msg.get('timestamp')}: \"{msg.get('content')}\""

            hint = msg.get("classification_hint", "contextual")
            classification = EvidenceClassification.CONTEXTUAL
            if hint == "speculation":
                classification = EvidenceClassification.UNVERIFIED
            elif hint == "contradiction_to_ddos":
                classification = EvidenceClassification.CONTRADICTING
            elif hint == "confirmed_finding":
                classification = EvidenceClassification.SUPPORTING

            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="slack_message",
                    source_id=msg_id,
                    title=f"Slack discussion in {channel} by {author}",
                    content=content,
                    service_id=None,
                    timestamp=msg.get("timestamp"),
                    citation={
                        "file_name": f"slack_export_{channel.replace('#', '')}.json",
                        "line_start": None,
                        "line_end": None,
                        "page": None,
                    },
                    retrieval_method="keyword_search",
                    relevance_score=0.8,
                    classification=classification,
                )
            )
        return items

    def retrieve_customer_sla(self, customer_id: str) -> dict[str, Any] | None:
        return dl_search_sla(customer_id=customer_id)

    def search_visual_evidence(
        self, query: str, incident_id: str | None = None, limit: int = 3
    ) -> list[EvidenceItem]:
        raw_assets = dl_search_visual_evidence(query=query, incident_id=incident_id, limit=limit)
        items = []
        for asset in raw_assets:
            asset_id = asset.get("asset_id", "ASSET-UNKNOWN")
            file_id = asset.get("file_id", asset_id)
            content = (
                f"Visual screenshot ({asset.get('title')}): {asset.get('description')} "
                f"[Asset API: /api/evidence/assets/{file_id}]"
            )
            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="grafana_screenshot",
                    source_id=asset_id,
                    title=asset.get("title", "Monitoring Dashboard Screenshot"),
                    content=content,
                    service_id=None,
                    timestamp=asset.get("timestamp"),
                    citation={
                        "file_name": f"{file_id}.png",
                        "line_start": None,
                        "line_end": None,
                        "page": None,
                    },
                    retrieval_method="multimodal_search",
                    relevance_score=0.9,
                    classification=EvidenceClassification.SUPPORTING,
                )
            )
        return items

    def get_visual_asset(self, file_id: str) -> tuple[bytes, str] | None:
        return dl_get_visual_asset(file_id=file_id)


adapter = DataLayerAdapter()
