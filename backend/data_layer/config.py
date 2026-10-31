"""
backend/data_layer/config.py
----------------------------
Central configuration loaded from environment variables.
All other modules import from here — never read os.environ directly.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load .env from the data_layer directory (or parent dirs)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env.example"), override=False)


@dataclass(frozen=True)
class _Config:
    # ── MongoDB ────────────────────────────────────────────────────────────────
    mongodb_uri: str = field(
        default_factory=lambda: os.environ.get(
            "MONGODB_URI",
            "mongodb://aegisrca:dev-only-change-this@localhost:27017/"
            "?authSource=admin&directConnection=true",
        )
    )
    mongodb_db_name: str = field(
        default_factory=lambda: os.environ.get("MONGODB_DB_NAME", "aegisrca")
    )

    # ── Voyage AI ──────────────────────────────────────────────────────────────
    voyage_api_key: str = field(
        default_factory=lambda: os.environ.get("VOYAGE_API_KEY", "")
    )
    voyage_model: str = field(
        default_factory=lambda: os.environ.get(
            "VOYAGE_MODEL", "voyage-multimodal-3.5"
        )
    )
    embedding_dimensions: int = field(
        default_factory=lambda: int(
            os.environ.get("EMBEDDING_DIMENSIONS", "1024")
        )
    )
    voyage_rerank_model: str = field(
        default_factory=lambda: os.environ.get(
            "VOYAGE_RERANK_MODEL", "rerank-2"
        )
    )

    # ── Collections ────────────────────────────────────────────────────────────
    col_services: str = "services"
    col_deployments: str = "deployments"
    col_knowledge: str = "knowledge_chunks"
    col_telemetry: str = "telemetry_events"
    col_messages: str = "incident_messages"
    col_sla: str = "sla_clauses"
    col_visual: str = "visual_evidence"
    col_incidents: str = "incidents"
    col_reports: str = "investigation_reports"

    # ── Search index names ─────────────────────────────────────────────────────
    vector_idx_knowledge: str = "knowledge_vector_idx"
    vector_idx_messages: str = "messages_vector_idx"
    vector_idx_visual: str = "visual_vector_idx"
    text_idx_knowledge: str = "knowledge_text_idx"
    text_idx_messages: str = "messages_text_idx"

    @property
    def embeddings_available(self) -> bool:
        return bool(self.voyage_api_key)


# Singleton
cfg = _Config()

