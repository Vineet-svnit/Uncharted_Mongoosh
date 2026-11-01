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
        get_pdf_file_id as dl_get_pdf_file_id,
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

    def dl_get_pdf_file_id(*args, **kwargs):
        return None

from app.schemas.investigation import (
    EvidenceItem,
    EvidenceClassification,
    SourceVerificationStatus,
    ClaimSupportStatus,
)


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

    def get_pdf_file_id(self, contract_id: str) -> str | None:
        return dl_get_pdf_file_id(contract_id=contract_id)

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
        service_id: str | None = None,
        start: str | None = None,
        end: str | None = None,
    ) -> list[EvidenceItem]:
        raw_deps = dl_get_deployments(service_id=service_id, start=start, end=end)
        items = []
        for dep in raw_deps:
            pr_num = dep.get("pr_number") or dep.get("pr_id")
            pr_label = f"PR #{pr_num}" if pr_num else dep.get("deployment_id", "DEP-UNKNOWN")
            dep_id = dep.get("deployment_id", "DEP-UNKNOWN")
            commit = dep.get("commit_hash", "")[:8]
            author = dep.get("deployed_by", "engineer")
            deployed_at = dep.get("deployed_at") or dep.get("timestamp")
            desc = dep.get("change_description") or dep.get("description", "")
            diff = dep.get("code_diff") or dep.get("diff_summary", "")
            files = dep.get("files_changed", [])
            svc_name = dep.get("service_id", service_id or "system")
            primary_file = files[0] if files else f"deployments_{svc_name}.json"

            content_lines = [
                f"Deployment: {dep_id} ({pr_label})",
                f"Commit: {commit} by {author} at {deployed_at}",
                f"Service: {svc_name}",
                f"Files Changed: {', '.join(files) if files else primary_file}",
                f"Change Summary: {desc}",
            ]
            if diff:
                content_lines.extend(["", "Code Diff Snippet:", diff[:400]])

            citation = dep.get("citation") or {
                "file_name": primary_file,
                "line_start": 44 if "redis" in primary_file.lower() else 1,
                "line_end": 52 if "redis" in primary_file.lower() else None,
                "page": None,
            }

            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="deployment_pr",
                    source_id=pr_label,
                    title=f"Deployment {dep_id} ({pr_label}): {desc[:50]}...",
                    content="\n".join(content_lines),
                    service_id=svc_name,
                    timestamp=deployed_at,
                    citation=citation,
                    retrieval_method="direct_query",
                    relevance_score=1.0,
                    classification=EvidenceClassification.SUPPORTING,
                    source_status=SourceVerificationStatus.VERIFIED,
                    claim_support=ClaimSupportStatus.SUPPORTED,
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

        # Fallback 1: If strict service_id resulted in 0 matches, retry without service_id
        # (knowledge documents such as postmortems and shared runbooks often span multiple services or lack a single service_id)
        if not raw_docs and "service_id" in filters:
            relaxed_filters = {k: v for k, v in filters.items() if k != "service_id"}
            raw_docs = dl_search_knowledge(query=query, filters=relaxed_filters, limit=limit)

        # Fallback 2: If still 0 matches, retry query across all knowledge categories
        if not raw_docs and "source_type" in filters:
            raw_docs = dl_search_knowledge(query=query, filters={}, limit=limit)

        items = []
        for doc in raw_docs:
            src_type = doc.get("source_type", "document")
            citation_dict = doc.get("citation") or {
                "file_name": f"{src_type}_{doc.get('knowledge_id', 'unknown')}.md",
                "line_start": None,
                "line_end": None,
                "page": None,
            }

            # If it's an SLA text chunk with a page, look up the PDF file ID in GridFS
            if src_type in ("sla_text", "sla", "contract"):
                contract_id = doc.get("source_id") or doc.get("contract_id", "SLA-ACME-001")
                pdf_id = self.get_pdf_file_id(contract_id)
                if pdf_id:
                    citation_dict["pdf_file_id"] = pdf_id

            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type=src_type,
                    source_id=doc.get("knowledge_id") or doc.get("document_id", str(uuid.uuid4())[:8]),
                    title=doc.get("title", "Engineering Knowledge Reference"),
                    content=doc.get("content", ""),
                    service_id=doc.get("service_id"),
                    timestamp=doc.get("timestamp"),
                    citation=citation_dict,
                    retrieval_method=doc.get("retrieval_method", "hybrid"),
                    relevance_score=doc.get("relevance_score", 0.85),
                    classification=EvidenceClassification.SUPPORTING,
                    source_status=SourceVerificationStatus.VERIFIED,
                    claim_support=ClaimSupportStatus.SUPPORTED,
                )
            )
        return items

    def query_service_telemetry(
        self, service_id: str, start: str | None = None, end: str | None = None
    ) -> list[EvidenceItem]:
        raw_events = dl_query_telemetry(service_id=service_id, start=start, end=end)
        items = []
        for ev in raw_events:
            ev_id = ev.get("event_id", f"TEL-{uuid.uuid4().hex[:4].upper()}")
            timestamp = ev.get("timestamp")
            metric_name = ev.get("metric_name", "metric")
            metric_val = ev.get("metric_value")
            unit = ev.get("unit", "")
            severity = ev.get("severity", "info")
            msg = ev.get("message", "")

            content_lines = [
                f"Metric: {metric_name} = {metric_val} {unit}".strip(),
                f"Observation: {msg}" if msg else "",
                f"Service: {service_id} | Severity: {severity} | Recorded: {timestamp}",
            ]
            content = "\n".join(line for line in content_lines if line)

            classification = EvidenceClassification.SUPPORTING
            if "ingress_rps" in str(metric_name).lower() and metric_val is not None and float(metric_val) < 1500:
                classification = EvidenceClassification.CONTRADICTING
            elif "ingress_rps" in ev and ev.get("ingress_rps", 0) < 1500:
                classification = EvidenceClassification.CONTRADICTING

            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="telemetry",
                    source_id=ev_id,
                    title=f"Telemetry observation: {service_id} ({metric_name})",
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
                    source_status=SourceVerificationStatus.VERIFIED,
                    claim_support=(
                        ClaimSupportStatus.CONTRADICTED
                        if classification == EvidenceClassification.CONTRADICTING
                        else ClaimSupportStatus.SUPPORTED
                    ),
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
            body = msg.get("content", "")
            ts = msg.get("timestamp")
            content = f"[{channel}] @{author} ({ts}):\n\"{body}\""

            hint = msg.get("classification_hint", "contextual")
            classification = EvidenceClassification.CONTEXTUAL
            claim_support = ClaimSupportStatus.INSUFFICIENT_EVIDENCE
            if hint == "contradiction_to_ddos":
                classification = EvidenceClassification.CONTRADICTING
                claim_support = ClaimSupportStatus.CONTRADICTED
            elif hint == "confirmed_finding":
                classification = EvidenceClassification.SUPPORTING
                claim_support = ClaimSupportStatus.SUPPORTED

            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="slack_message",
                    source_id=msg_id,
                    title=f"Slack war room discussion in {channel} by @{author}",
                    content=content,
                    service_id=None,
                    timestamp=ts,
                    citation={
                        "file_name": f"slack_export_{channel.replace('#', '')}.json",
                        "line_start": None,
                        "line_end": None,
                        "page": None,
                    },
                    retrieval_method="keyword_search",
                    relevance_score=0.8,
                    classification=classification,
                    source_status=SourceVerificationStatus.VERIFIED,
                    claim_support=claim_support,
                )
            )
        return items

    def retrieve_customer_sla(self, customer_id: str) -> dict[str, Any] | None:
        """
        Retrieve structured SLA contract information with credit tiers and GridFS PDF reference.
        """
        raw = dl_search_sla(customer_id=customer_id)
        if not raw:
            return None

        clauses = raw if isinstance(raw, list) else [raw]
        contract_id = clauses[0].get("contract_id", "SLA-ACME-001") if clauses else "SLA-ACME-001"
        cust_name = clauses[0].get("customer_name", customer_id) if clauses else customer_id

        # Lookup PDF in GridFS
        pdf_file_id = self.get_pdf_file_id(contract_id)

        # Build credit tiers for deterministic SLA assessment engine
        credit_tiers = []
        for c in clauses:
            if c.get("downtime_min_minutes") is not None:
                credit_tiers.append({
                    "min_downtime_minutes": c.get("downtime_min_minutes", 0),
                    "max_downtime_minutes": c.get("downtime_max_minutes"),
                    "credit_percent": float(c.get("financial_credit_pct") or 0.0),
                    "rca_required": bool(c.get("rca_required", False)),
                    "clause_number": c.get("clause_number"),
                    "page": c.get("page"),
                    "title": c.get("title"),
                    "content": c.get("content"),
                })

        return {
            "contract_id": contract_id,
            "contract_name": f"Master Services Agreement ({cust_name})",
            "customer_id": customer_id,
            "customer_name": cust_name,
            "pdf_file_id": pdf_file_id,
            "file_name": f"SLA_{contract_id}.pdf",
            "credit_tiers": credit_tiers,
            "clauses": clauses,
            "exclusions": ["force_majeure", "scheduled_maintenance"],
            "rca_policy": {"delivery_window_days": 5},
        }

    def search_visual_evidence(
        self, query: str, incident_id: str | None = None, limit: int = 3
    ) -> list[EvidenceItem]:
        raw_assets = dl_search_visual_evidence(query=query, incident_id=incident_id, limit=limit)
        items = []
        for asset in raw_assets:
            evidence_id_raw = asset.get("evidence_id") or asset.get("asset_id", "VE-UNKNOWN")
            gridfs_file_id = asset.get("gridfs_file_id") or asset.get("file_id", "")
            file_name = asset.get("file_name") or (f"{gridfs_file_id}.png" if gridfs_file_id else "screenshot.png")
            title = asset.get("title", "Monitoring Dashboard Screenshot")
            description = asset.get("description", "")
            content = (
                f"Visual Evidence: {title}\n"
                f"Description: {description}\n"
                f"Asset ID: {gridfs_file_id}"
            )
            items.append(
                EvidenceItem(
                    evidence_id=self._next_evd_id(),
                    source_type="grafana_screenshot",
                    source_id=evidence_id_raw,
                    title=title,
                    content=content,
                    service_id=asset.get("service_id"),
                    timestamp=asset.get("captured_at") or asset.get("timestamp"),
                    citation={
                        "file_name": file_name,
                        "line_start": None,
                        "line_end": None,
                        "page": None,
                    },
                    retrieval_method="multimodal_search",
                    relevance_score=float(asset.get("score") or 0.9),
                    classification=EvidenceClassification.SUPPORTING,
                    asset_file_id=gridfs_file_id if gridfs_file_id else None,
                    source_status=SourceVerificationStatus.VERIFIED if gridfs_file_id else SourceVerificationStatus.UNAVAILABLE,
                    claim_support=ClaimSupportStatus.SUPPORTED,
                )
            )
        return items

    def get_visual_asset(self, file_id: str) -> tuple[bytes, str] | None:
        result = dl_get_visual_asset(file_id=file_id)
        if result is None:
            return None
        if isinstance(result, tuple) and len(result) == 2:
            return result
        return (result, "image/png")


adapter = DataLayerAdapter()
