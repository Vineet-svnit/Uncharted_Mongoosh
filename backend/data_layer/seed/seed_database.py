# -*- coding: utf-8 -*-
"""
backend/data_layer/seed/seed_database.py
-----------------------------------------
Master seeding script.

Usage:
    python -m data_layer.seed.seed_database [--reset] [--skip-embeddings]

Flags:
    --reset             Drop and recreate all AegisRCA collections before seeding.
    --skip-embeddings   Skip Voyage AI embedding generation. Structured, graph and
                        keyword search will work; semantic / multimodal search will not.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone
from typing import Any

import gridfs
from pymongo import UpdateOne

# Ensure the package root is on PYTHONPATH when invoked with -m
if __package__ is None:  # pragma: no cover
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))

from data_layer.config import cfg
from data_layer.index_manager import (
    check_mongodb_version,
    ensure_all_indexes,
    wait_for_search_indexes,
)
from data_layer.mongo import get_db, get_gridfs

from .generate_assets import (
    extract_pdf_text,
    generate_grafana_screenshot_1,
    generate_grafana_screenshot_2,
    generate_sla_pdfs,
)
from .generate_dataset import (
    generate_deployments,
    generate_incident,
    generate_postmortems,
    generate_runbooks,
    generate_services,
    generate_slack_messages,
    generate_sla_data,
    generate_telemetry,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("seed")

KNOWN_COLLECTIONS = [
    cfg.col_services, cfg.col_deployments, cfg.col_knowledge,
    cfg.col_telemetry, cfg.col_messages, cfg.col_sla,
    cfg.col_visual, cfg.col_incidents, cfg.col_reports,
]

GRIDFS_BUCKET = "fs"


# ─────────────────────────────────────────────────────────────────────────────
# Reset
# ─────────────────────────────────────────────────────────────────────────────

def reset_database(db) -> None:
    log.info("Resetting AegisRCA collections …")
    existing_cols = db.list_collection_names()
    for name in KNOWN_COLLECTIONS:
        if name in existing_cols:
            db[name].delete_many({})
            log.info("  Cleared documents in collection: %s", name)
        else:
            db.create_collection(name)
            log.info("  Created collection: %s", name)
    # GridFS
    if "fs.files" in existing_cols:
        db["fs.files"].delete_many({})
    if "fs.chunks" in existing_cols:
        db["fs.chunks"].delete_many({})
    log.info("  Cleared GridFS collections.")


# ─────────────────────────────────────────────────────────────────────────────
# Chunking helpers
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> list[str]:
    """Split text into overlapping character-level chunks."""
    if len(text) <= chunk_size:
        return [text.strip()]
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end].strip())
        start += chunk_size - overlap
    return [c for c in chunks if c]


def _make_chunk(
    doc_id: str,
    source_id: str,
    source_type: str,
    source_file: str,
    title: str,
    content: str,
    service_id: str | None = None,
    incident_id: str | None = None,
    customer_id: str | None = None,
    environment: str | None = None,
    timestamp: str | None = None,
    citation: dict | None = None,
) -> dict:
    return {
        "document_id": doc_id,
        "source_id": source_id,
        "source_type": source_type,
        "source_file": source_file,
        "title": title,
        "content": content,
        "service_id": service_id,
        "incident_id": incident_id,
        "customer_id": customer_id,
        "environment": environment,
        "timestamp": timestamp,
        "citation": citation or {"file_name": source_file,
                                 "line_start": None, "line_end": None, "page": None},
        "embedding": None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Build all knowledge chunks
# ─────────────────────────────────────────────────────────────────────────────

def build_knowledge_chunks(
    deployments: list[dict],
    runbooks: list[dict],
    postmortems: list[dict],
    sla_pdfs: list[dict],          # {contract_id, customer_id, pdf_bytes, …}
    sla_raw: list[dict],           # raw SLA contract dicts with clauses
) -> list[dict]:
    chunks: list[dict] = []

    # ── Deployment / PR diffs ─────────────────────────────────────────────────
    for dep in deployments:
        pr = dep["pr_number"]
        full_content = (
            f"PR #{pr}: {dep['change_description']}\n\n"
            f"Service: {dep['service_id']}\n"
            f"Deployed at: {dep['deployed_at']}\n"
            f"Commit: {dep['commit_hash']}\n"
            f"Files changed: {', '.join(dep['files_changed'])}\n\n"
            f"Code diff:\n{dep['code_diff']}\n\n"
            f"Previous config: {dep['previous_config']}\n"
            f"Updated config: {dep['updated_config']}"
        )
        sub_chunks = _chunk_text(full_content, chunk_size=1000)
        for j, chunk_text in enumerate(sub_chunks):
            suffix = f"-{j}" if len(sub_chunks) > 1 else ""
            chunks.append(_make_chunk(
                doc_id=f"chunk-pr-{pr}{suffix}",
                source_id=f"PR-{pr}",
                source_type="pr_diff",
                source_file=dep.get("source_file", f"GitHub_PR_{pr}.json"),
                title=f"PR #{pr}: {dep['change_description'][:60]}",
                content=chunk_text,
                service_id=dep["service_id"],
                incident_id=(
                    "INC-2026-10-28-001"
                    if pr in (812, 813)
                    else None
                ),
                timestamp=dep["deployed_at"],
                citation=dep.get("citation"),
            ))

    # ── Runbooks ──────────────────────────────────────────────────────────────
    for rb in runbooks:
        sub_chunks = _chunk_text(rb["content"], chunk_size=900)
        for j, chunk_text in enumerate(sub_chunks):
            suffix = f"-{j}" if len(sub_chunks) > 1 else ""
            chunks.append(_make_chunk(
                doc_id=f"chunk-rb-{rb['runbook_id'].lower()}{suffix}",
                source_id=rb["runbook_id"],
                source_type="runbook",
                source_file=f"{rb['runbook_id']}_{rb['title'].replace(' ', '_')}.md",
                title=rb["title"],
                content=chunk_text,
                service_id=rb.get("service_id"),
            ))

    # ── Postmortems ───────────────────────────────────────────────────────────
    for pm in postmortems:
        sub_chunks = _chunk_text(pm["content"], chunk_size=900)
        for j, chunk_text in enumerate(sub_chunks):
            suffix = f"-{j}" if len(sub_chunks) > 1 else ""
            chunks.append(_make_chunk(
                doc_id=f"chunk-pm-{pm['postmortem_id'].lower()}{suffix}",
                source_id=pm["postmortem_id"],
                source_type="postmortem",
                source_file=f"Postmortem_{pm['postmortem_id']}.md",
                title=pm["title"],
                content=chunk_text,
                incident_id=pm.get("incident_id"),
            ))

    # ── SLA text chunks (from extracted PDF) ──────────────────────────────────
    for pdf_info in sla_pdfs:
        contract_id = pdf_info["contract_id"]
        customer_id = pdf_info["customer_id"]
        pages = extract_pdf_text(pdf_info["pdf_bytes"])
        for page_info in pages:
            page_num = page_info["page_number"]
            page_text = page_info["text"].strip()
            if not page_text:
                continue
            sub_chunks = _chunk_text(page_text, chunk_size=800)
            for j, chunk_text in enumerate(sub_chunks):
                suffix = f"-{j}" if len(sub_chunks) > 1 else ""
                chunks.append(_make_chunk(
                    doc_id=f"chunk-sla-{contract_id.lower()}-p{page_num}{suffix}",
                    source_id=contract_id,
                    source_type="sla_text",
                    source_file=pdf_info["file_name"],
                    title=f"SLA {contract_id} — Page {page_num}",
                    content=chunk_text,
                    customer_id=customer_id,
                    citation={"file_name": pdf_info["file_name"],
                              "line_start": None, "line_end": None,
                              "page": page_num},
                ))

    # ── Incident summary ──────────────────────────────────────────────────────
    chunks.append(_make_chunk(
        doc_id="chunk-inc-main",
        source_id="INC-2026-10-28-001",
        source_type="incident_summary",
        source_file="INC-2026-10-28-001.json",
        title="Incident INC-2026-10-28-001 — Checkout API 504 Gateway Timeout",
        content=(
            "Incident INC-2026-10-28-001\n"
            "Date: October 28, 2026\n"
            "Affected service: checkout-api\n"
            "Customer: Acme Corp\n"
            "Investigation window: 14:00–14:25 UTC\n"
            "Customer impact: 14:02–14:25 UTC (23 minutes)\n\n"
            "Root cause: PR #812 changed redis_pool_max_connections from 500 to 50 on "
            "auth-service. Pool exhaustion caused authentication timeouts. Internal retries "
            "increased ~15×. Checkout API returned 504 Gateway Timeout errors.\n\n"
            "Resolution: PR #813 (rollback) deployed at 14:22 UTC. Services recovered by "
            "14:25 UTC.\n\n"
            "SLA impact: 23-minute downtime. Acme Corp SLA clause 3.2 applies: "
            "RCA required, no financial credit."
        ),
        incident_id="INC-2026-10-28-001",
        customer_id="acme-corp",
        timestamp="2026-10-28T14:25:00Z",
    ))

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Build SLA clause records
# ─────────────────────────────────────────────────────────────────────────────

def build_sla_clauses(sla_raw: list[dict]) -> list[dict]:
    clauses = []
    for contract in sla_raw:
        for clause in contract["clauses"]:
            clauses.append({
                "clause_id": f"clause-{contract['contract_id']}-{clause['clause_number']}",
                "contract_id": contract["contract_id"],
                "customer_id": contract["customer_id"],
                "customer_name": contract["customer_name"],
                "contract_version": contract["contract_version"],
                "clause_number": clause["clause_number"],
                "page": clause["page"],
                "title": clause["title"],
                "content": clause["content"],
                "downtime_min_minutes": clause.get("downtime_min_minutes"),
                "downtime_max_minutes": clause.get("downtime_max_minutes"),
                "financial_credit_pct": clause.get("financial_credit_pct"),
                "rca_required": clause.get("rca_required"),
                "is_active": True,
            })
    return clauses


# ─────────────────────────────────────────────────────────────────────────────
# Upsert helpers
# ─────────────────────────────────────────────────────────────────────────────

def _upsert_many(collection, docs: list[dict], id_field: str) -> int:
    if not docs:
        return 0
    ops = [
        UpdateOne(
            {id_field: doc[id_field]},
            {"$set": doc},
            upsert=True,
        )
        for doc in docs
    ]
    result = collection.bulk_write(ops, ordered=False)
    return result.upserted_count + result.modified_count


# ─────────────────────────────────────────────────────────────────────────────
# GridFS upload
# ─────────────────────────────────────────────────────────────────────────────

def _upload_gridfs(gfs: gridfs.GridFS, file_bytes: bytes, filename: str,
                   content_type: str) -> str:
    """Upload bytes to GridFS; returns the str(ObjectId)."""
    # Delete existing file with same name first (idempotent)
    for existing in gfs.find({"filename": filename}):
        gfs.delete(existing._id)
    file_id = gfs.put(file_bytes, filename=filename, content_type=content_type)
    return str(file_id)


# ─────────────────────────────────────────────────────────────────────────────
# Embedding generation
# ─────────────────────────────────────────────────────────────────────────────

def embed_knowledge_chunks(db, chunks: list[dict]) -> None:
    import time
    from data_layer.embeddings import embed_texts_batched  # noqa: PLC0415

    texts = [c["content"] for c in chunks]
    log.info("Generating embeddings for %d knowledge chunks …", len(texts))
    embeddings = embed_texts_batched(texts, batch_size=50)
    col = db[cfg.col_knowledge]
    for chunk, emb in zip(chunks, embeddings):
        col.update_one(
            {"document_id": chunk["document_id"]},
            {"$set": {"embedding": emb}},
        )
    log.info("Knowledge chunk embeddings stored.")
    log.info("Waiting 21s for Voyage AI rate limit window (3 RPM free tier)...")
    time.sleep(21)


def embed_messages(db, messages: list[dict]) -> None:
    import time
    from data_layer.embeddings import embed_texts_batched  # noqa: PLC0415

    texts = [m["text"] for m in messages]
    log.info("Generating embeddings for %d Slack messages …", len(texts))
    embeddings = embed_texts_batched(texts, batch_size=50)
    col = db[cfg.col_messages]
    for msg, emb in zip(messages, embeddings):
        col.update_one(
            {"message_id": msg["message_id"]},
            {"$set": {"embedding": emb}},
        )
    log.info("Message embeddings stored.")
    log.info("Waiting 21s for Voyage AI rate limit window (3 RPM free tier)...")
    time.sleep(21)


def embed_visual(db, visual_docs: list[dict], image_bytes_list: list[bytes]) -> None:
    from data_layer.embeddings import embed_images_with_text  # noqa: PLC0415

    col = db[cfg.col_visual]
    items = [(img, vdoc["description"]) for vdoc, img in zip(visual_docs, image_bytes_list)]
    log.info("Generating multimodal embeddings for %d screenshots in a single batch …", len(items))
    embeddings = embed_images_with_text(items)
    for vdoc, emb in zip(visual_docs, embeddings):
        col.update_one(
            {"evidence_id": vdoc["evidence_id"]},
            {"$set": {"embedding": emb}},
        )
        log.info("  Stored embedding for %s", vdoc["evidence_id"])
    log.info("Visual evidence embeddings stored.")


# ─────────────────────────────────────────────────────────────────────────────
# Verification
# ─────────────────────────────────────────────────────────────────────────────

def verify_counts(db) -> bool:
    ok = True
    checks = [
        (cfg.col_services, 8, "service records"),
        (cfg.col_deployments, 9, "deployment records"),
        (cfg.col_messages, 50, "Slack messages"),
        (cfg.col_telemetry, 180, "telemetry events"),
        (cfg.col_incidents, 1, "incident records"),
    ]
    for col_name, expected, label in checks:
        actual = db[col_name].count_documents({})
        status = "✓" if actual == expected else "✗"
        if actual != expected:
            ok = False
        log.info("  %s %s: %d / %d", status, label, actual, expected)

    # Runbooks (source_type = runbook)
    rb_count = db[cfg.col_knowledge].count_documents({"source_type": "runbook"})
    sla_chunks = db[cfg.col_knowledge].count_documents({"source_type": "sla_text"})
    pm_chunks = db[cfg.col_knowledge].count_documents({"source_type": "postmortem"})
    sla_clauses = db[cfg.col_sla].count_documents({})
    visual = db[cfg.col_visual].count_documents({})

    log.info("  ✓ runbook chunks: %d", rb_count)
    log.info("  ✓ postmortem chunks: %d", pm_chunks)
    log.info("  ✓ SLA text chunks: %d", sla_chunks)
    log.info("  ✓ SLA clauses: %d", sla_clauses)
    log.info("  ✓ visual evidence records: %d", visual)

    return ok


def print_summary(db, skip_embeddings: bool) -> None:
    log.info("=" * 60)
    log.info("AegisRCA Dataset Summary")
    log.info("=" * 60)
    for col_name in KNOWN_COLLECTIONS:
        n = db[col_name].count_documents({})
        log.info("  %-30s %d documents", col_name, n)

    chunks_with_emb = db[cfg.col_knowledge].count_documents(
        {"embedding": {"$ne": None}}
    )
    msgs_with_emb = db[cfg.col_messages].count_documents(
        {"embedding": {"$ne": None}}
    )
    vis_with_emb = db[cfg.col_visual].count_documents(
        {"embedding": {"$ne": None}}
    )
    log.info("-" * 60)
    log.info("  knowledge_chunks with embeddings: %d", chunks_with_emb)
    log.info("  incident_messages with embeddings: %d", msgs_with_emb)
    log.info("  visual_evidence with embeddings: %d", vis_with_emb)
    if skip_embeddings:
        log.warning(
            "⚠  Embeddings were SKIPPED. "
            "Semantic ($vectorSearch) and multimodal retrieval will not work."
        )
    log.info("=" * 60)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the AegisRCA database.")
    parser.add_argument("--reset", action="store_true",
                        help="Drop and recreate all AegisRCA collections.")
    parser.add_argument("--skip-embeddings", action="store_true",
                        help="Skip Voyage AI embedding generation.")
    args = parser.parse_args()

    skip_embeddings = args.skip_embeddings or (not cfg.voyage_api_key)
    if not cfg.voyage_api_key and not args.skip_embeddings:
        log.warning(
            "VOYAGE_API_KEY not set — running in --skip-embeddings mode automatically."
        )

    log.info("Connecting to MongoDB at %s …", cfg.mongodb_uri.split("@")[-1])
    db = get_db()
    gfs = get_gridfs()

    version = check_mongodb_version(db)

    if args.reset:
        reset_database(db)

    # ── 1. Generate raw data ──────────────────────────────────────────────────
    log.info("Generating synthetic dataset …")
    services = generate_services()
    deployments = generate_deployments()
    messages = generate_slack_messages()
    telemetry = generate_telemetry()
    runbooks = generate_runbooks()
    postmortems = generate_postmortems()
    incident = generate_incident()
    sla_raw = generate_sla_data()

    # ── 2. Generate PDFs ──────────────────────────────────────────────────────
    log.info("Generating SLA PDFs …")
    sla_pdfs = generate_sla_pdfs(sla_raw)

    # ── 3. Generate screenshots ───────────────────────────────────────────────
    log.info("Generating Grafana-style screenshots …")
    png1_bytes, png1_meta = generate_grafana_screenshot_1()
    png2_bytes, png2_meta = generate_grafana_screenshot_2()

    # ── 4. Build knowledge chunks ─────────────────────────────────────────────
    log.info("Building knowledge chunks …")
    knowledge_chunks = build_knowledge_chunks(
        deployments, runbooks, postmortems, sla_pdfs, sla_raw
    )

    # ── 5. Build SLA clause records ───────────────────────────────────────────
    sla_clauses = build_sla_clauses(sla_raw)

    # ── 6. Create indexes ─────────────────────────────────────────────────────
    log.info("Creating MongoDB indexes …")
    ensure_all_indexes(db)

    # ── 7. Insert structured data ─────────────────────────────────────────────
    log.info("Inserting services (%d) …", len(services))
    _upsert_many(db[cfg.col_services], services, "service_id")

    log.info("Inserting deployments (%d) …", len(deployments))
    _upsert_many(db[cfg.col_deployments], deployments, "deployment_id")

    log.info("Inserting telemetry events (%d) …", len(telemetry))
    _upsert_many(db[cfg.col_telemetry], telemetry, "event_id")

    log.info("Inserting Slack messages (%d) …", len(messages))
    _upsert_many(db[cfg.col_messages], messages, "message_id")

    log.info("Inserting knowledge chunks (%d) …", len(knowledge_chunks))
    _upsert_many(db[cfg.col_knowledge], knowledge_chunks, "document_id")

    log.info("Inserting SLA clauses (%d) …", len(sla_clauses))
    _upsert_many(db[cfg.col_sla], sla_clauses, "clause_id")

    log.info("Inserting incident record …")
    _upsert_many(db[cfg.col_incidents], [incident], "incident_id")

    # ── 8. GridFS — PDFs ─────────────────────────────────────────────────────
    log.info("Uploading PDFs to GridFS …")
    for pdf_info in sla_pdfs:
        fid = _upload_gridfs(gfs, pdf_info["pdf_bytes"], pdf_info["file_name"],
                             "application/pdf")
        log.info("  Uploaded %s → GridFS ID %s", pdf_info["file_name"], fid)

    # ── 9. GridFS — Screenshots + visual_evidence records ────────────────────
    log.info("Uploading screenshots to GridFS …")
    visual_docs = []
    image_bytes_list = []

    for img_bytes, meta in [(png1_bytes, png1_meta), (png2_bytes, png2_meta)]:
        fid = _upload_gridfs(gfs, img_bytes, meta["file_name"], "image/png")
        log.info("  Uploaded %s → GridFS ID %s", meta["file_name"], fid)
        vdoc = {
            "evidence_id": meta["evidence_id"],
            "incident_id": meta["incident_id"],
            "title": meta["title"],
            "description": meta["description"],
            "gridfs_file_id": fid,
            "file_name": meta["file_name"],
            "mime_type": meta["mime_type"],
            "captured_at": meta["captured_at"],
            "embedding": None,
        }
        visual_docs.append(vdoc)
        image_bytes_list.append(img_bytes)

    _upsert_many(db[cfg.col_visual], visual_docs, "evidence_id")

    # ── 10. Embeddings ────────────────────────────────────────────────────────
    if not skip_embeddings:
        log.info("Generating embeddings (this may take a few minutes) …")
        embed_knowledge_chunks(db, knowledge_chunks)
        embed_messages(db, messages)
        embed_visual(db, visual_docs, image_bytes_list)
    else:
        log.info("Skipping embedding generation.")

    # ── 11. Wait for search indexes ───────────────────────────────────────────
    log.info("Waiting for Atlas Search indexes to become READY …")
    ready = wait_for_search_indexes(db, timeout=300)
    if not ready:
        log.warning(
            "Some search indexes are not yet READY. "
            "Vector and text search may fail until they are built."
        )

    # ── 12. Verify ────────────────────────────────────────────────────────────
    log.info("Verifying dataset counts …")
    verify_counts(db)

    # ── 13. Summary ───────────────────────────────────────────────────────────
    print_summary(db, skip_embeddings)


if __name__ == "__main__":
    main()

