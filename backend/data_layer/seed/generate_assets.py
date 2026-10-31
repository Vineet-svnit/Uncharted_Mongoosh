# -*- coding: utf-8 -*-
"""
backend/data_layer/seed/generate_assets.py
--------------------------------------------
Generates binary assets:
  • Two synthetic SLA PDFs (via ReportLab)
  • PDF text extraction (via PyMuPDF)
  • Two synthetic Grafana-style dashboard PNGs (via Matplotlib)

No MongoDB access here — returns raw bytes and metadata dicts.
"""

from __future__ import annotations

import io
import textwrap
from datetime import datetime, timedelta, timezone
from typing import Any

from .scenario import (
    INCIDENT_ID,
    NORMAL_INGRESS_RPS,
    REDIS_POOL_AFTER,
    REDIS_POOL_BEFORE,
    RETRY_MULTIPLIER,
    T_IMPACT_START,
    T_RECOVERY,
    T_ROLLBACK,
)


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATION
# ─────────────────────────────────────────────────────────────────────────────

def _build_pdf(sla_data: dict) -> bytes:
    """Render one SLA contract as a proper PDF using ReportLab."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        HRFlowable,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ContractTitle",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#1a1a2e"),
    )
    h2_style = ParagraphStyle(
        "ClauseHeading",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=10,
        spaceAfter=6,
        textColor=colors.HexColor("#16213e"),
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=10,
        leading=14,
        spaceAfter=8,
    )
    meta_style = ParagraphStyle(
        "Meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.grey,
        spaceAfter=4,
    )

    story = []

    # Title block
    story.append(Paragraph(
        f"Service Level Agreement<br/>{sla_data['customer_name']}",
        title_style,
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#1a1a2e")))
    story.append(Spacer(1, 0.3 * cm))

    # Metadata table
    meta_rows = [
        ["Contract ID:", sla_data["contract_id"]],
        ["Contract Version:", sla_data["contract_version"]],
        ["Customer ID:", sla_data["customer_id"]],
        ["Effective Date:", sla_data["effective_date"]],
        ["Expiry Date:", sla_data["expiry_date"]],
        ["Availability Commitment:", f"{sla_data['availability_commitment_pct']}%"],
        ["Covered Services:", ", ".join(sla_data["covered_services"])],
    ]
    meta_table = Table(meta_rows, colWidths=[5 * cm, 11 * cm])
    meta_table.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.3 * cm))

    # Clauses
    for clause in sla_data["clauses"]:
        story.append(Paragraph(
            f"Clause {clause['clause_number']} — {clause['title']}", h2_style
        ))
        story.append(Paragraph(clause["content"], body_style))

        # If threshold clause, add a summary box
        if clause.get("downtime_min_minutes") is not None:
            lo = clause["downtime_min_minutes"]
            hi = clause.get("downtime_max_minutes")
            credit = clause.get("financial_credit_pct", 0)
            rca = clause.get("rca_required", False)
            range_str = (
                f"{lo}–{hi} min" if hi is not None else f"≥ {lo} min"
            )
            summary_rows = [
                ["Downtime Range:", range_str],
                ["Financial Credit:", f"{credit:.0f}%"],
                ["RCA Required:", "Yes" if rca else "No"],
            ]
            stbl = Table(summary_rows, colWidths=[5 * cm, 6 * cm])
            stbl.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f0f4ff")),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c8d0e0")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]))
            story.append(stbl)
            story.append(Spacer(1, 0.2 * cm))

    # Signature block
    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(
        "This agreement is binding from the Effective Date. "
        "This is a synthetic document generated for the AegisRCA demonstration system.",
        meta_style,
    ))

    doc.build(story)
    return buf.getvalue()


def generate_sla_pdfs(sla_data_list: list[dict]) -> list[dict]:
    """
    For each SLA contract dict, generate a PDF and return a list of:
      { contract_id, customer_id, file_name, pdf_bytes }
    """
    results = []
    for sla in sla_data_list:
        pdf_bytes = _build_pdf(sla)
        results.append({
            "contract_id": sla["contract_id"],
            "customer_id": sla["customer_id"],
            "customer_name": sla["customer_name"],
            "file_name": f"SLA_{sla['contract_id']}.pdf",
            "pdf_bytes": pdf_bytes,
        })
    return results


def extract_pdf_text(pdf_bytes: bytes) -> list[dict]:
    """
    Extract text from a PDF using PyMuPDF, returning a list of
    { page_number, text } dicts (1-indexed pages).
    """
    import fitz  # PyMuPDF  # noqa: PLC0415

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        pages.append({"page_number": page_num + 1, "text": text})
    doc.close()
    return pages


# ─────────────────────────────────────────────────────────────────────────────
# PNG GENERATION
# ─────────────────────────────────────────────────────────────────────────────

_GRAFANA_BG = "#111217"
_GRAFANA_PANEL = "#1b1e2a"
_GRAFANA_GRID = "#2a2d3a"
_GRAFANA_TEXT = "#d9d9d9"
_COLORS = ["#f2495c", "#ff9830", "#73bf69", "#5794f2", "#b877d9", "#fade2a"]


def _apply_grafana_style(fig, axes):
    """Apply a dark Grafana-inspired theme."""
    import matplotlib.pyplot as plt  # noqa: PLC0415

    fig.patch.set_facecolor(_GRAFANA_BG)
    for ax in (axes if hasattr(axes, "__iter__") else [axes]):
        ax.set_facecolor(_GRAFANA_PANEL)
        ax.tick_params(colors=_GRAFANA_TEXT, labelsize=8)
        ax.xaxis.label.set_color(_GRAFANA_TEXT)
        ax.yaxis.label.set_color(_GRAFANA_TEXT)
        ax.title.set_color(_GRAFANA_TEXT)
        for spine in ax.spines.values():
            spine.set_edgecolor(_GRAFANA_GRID)
        ax.grid(True, color=_GRAFANA_GRID, linewidth=0.5, linestyle="--")


def generate_grafana_screenshot_1() -> tuple[bytes, dict]:
    """
    Screenshot 1: Redis pool utilization + Auth timeouts + Checkout 504s.
    16:9 layout, 1920×1080.
    Returns (png_bytes, metadata_dict).
    """
    import random

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt
    import numpy as np

    rng = random.Random(42)

    # Time axis: 14:00 → 14:30 UTC, 1-minute resolution
    t_start = T_IMPACT_START - timedelta(minutes=2)
    t_end = T_RECOVERY + timedelta(minutes=5)
    minutes = int((t_end - t_start).total_seconds() / 60)
    times = [t_start + timedelta(minutes=m) for m in range(minutes)]

    def pool_util(t):
        if t < T_IMPACT_START:
            return rng.uniform(14, 18)
        if t < T_ROLLBACK:
            return 100.0
        if t < T_RECOVERY:
            elapsed = (t - T_ROLLBACK).total_seconds() / 60
            return max(0, 100 - elapsed * 30)
        return rng.uniform(10, 18)

    def auth_timeouts(t):
        if t < T_IMPACT_START:
            return rng.randint(0, 2)
        if t < T_ROLLBACK:
            return rng.randint(200, 230)
        if t < T_RECOVERY:
            elapsed = (t - T_ROLLBACK).total_seconds() / 60
            return max(0, int(220 - elapsed * 65))
        return rng.randint(0, 2)

    def checkout_504s(t):
        if t < T_IMPACT_START:
            return rng.randint(0, 1)
        if t < T_ROLLBACK:
            return rng.randint(900, 1000)
        if t < T_RECOVERY:
            elapsed = (t - T_ROLLBACK).total_seconds() / 60
            return max(0, int(950 - elapsed * 280))
        return rng.randint(0, 3)

    pool_vals = [pool_util(t) for t in times]
    timeout_vals = [auth_timeouts(t) for t in times]
    err_vals = [checkout_504s(t) for t in times]

    fig, axes = plt.subplots(3, 1, figsize=(19.2, 10.8), sharex=True)
    fig.suptitle(
        f"AegisRCA — Incident {INCIDENT_ID} — Oct 28 2026 14:00–14:30 UTC",
        color=_GRAFANA_TEXT, fontsize=14, fontweight="bold",
        y=0.98,
    )

    # Panel 1: Redis pool
    axes[0].plot(times, pool_vals, color=_COLORS[0], linewidth=2, label="redis_pool_utilization")
    axes[0].axhline(100, color=_COLORS[5], linestyle=":", linewidth=1, alpha=0.7)
    axes[0].set_title("Redis Connection Pool Utilization — auth-service", fontsize=10)
    axes[0].set_ylabel("Utilization %", fontsize=9)
    axes[0].set_ylim(-5, 115)
    axes[0].fill_between(times, pool_vals, alpha=0.15, color=_COLORS[0])
    axes[0].legend(loc="upper right", fontsize=8, facecolor=_GRAFANA_PANEL,
                   labelcolor=_GRAFANA_TEXT)

    # Panel 2: Auth timeouts
    axes[1].plot(times, timeout_vals, color=_COLORS[1], linewidth=2,
                 label="redis_connection_timeout_count")
    axes[1].set_title("Redis Connection Acquisition Timeouts — auth-service", fontsize=10)
    axes[1].set_ylabel("Timeouts / min", fontsize=9)
    axes[1].fill_between(times, timeout_vals, alpha=0.15, color=_COLORS[1])
    axes[1].legend(loc="upper right", fontsize=8, facecolor=_GRAFANA_PANEL,
                   labelcolor=_GRAFANA_TEXT)

    # Panel 3: 504 errors
    axes[2].plot(times, err_vals, color=_COLORS[2], linewidth=2,
                 label="http_504_count")
    axes[2].set_title("Checkout API — HTTP 504 Errors per Minute", fontsize=10)
    axes[2].set_ylabel("504 Errors / min", fontsize=9)
    axes[2].set_xlabel("Time (UTC)", fontsize=9)
    axes[2].fill_between(times, err_vals, alpha=0.15, color=_COLORS[2])
    axes[2].legend(loc="upper right", fontsize=8, facecolor=_GRAFANA_PANEL,
                   labelcolor=_GRAFANA_TEXT)

    # Event markers
    for ax in axes:
        ax.axvline(T_IMPACT_START, color="#f7da2e", linestyle="--",
                   linewidth=1.2, alpha=0.8, label=None)
        ax.axvline(T_ROLLBACK, color="#73bf69", linestyle="--",
                   linewidth=1.2, alpha=0.8, label=None)
        ax.axvline(T_RECOVERY, color="#5794f2", linestyle="--",
                   linewidth=1.2, alpha=0.8, label=None)

    # Format x-axis
    axes[2].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axes[2].xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 5)))
    fig.autofmt_xdate(rotation=0)

    # Annotations on top panel
    axes[0].annotate("PR #812 deployed\n(pool: 500→50)", xy=(T_IMPACT_START, 100),
                     xytext=(T_IMPACT_START + timedelta(minutes=1), 85),
                     color=_GRAFANA_TEXT, fontsize=7,
                     arrowprops=dict(arrowstyle="->", color=_GRAFANA_TEXT, lw=0.8))
    axes[0].annotate("Rollback PR #813", xy=(T_ROLLBACK, 80),
                     xytext=(T_ROLLBACK + timedelta(minutes=0.5), 60),
                     color=_GRAFANA_TEXT, fontsize=7,
                     arrowprops=dict(arrowstyle="->", color=_GRAFANA_TEXT, lw=0.8))
    axes[0].annotate("Recovered", xy=(T_RECOVERY, 15),
                     xytext=(T_RECOVERY + timedelta(minutes=0.5), 35),
                     color=_GRAFANA_TEXT, fontsize=7,
                     arrowprops=dict(arrowstyle="->", color=_GRAFANA_TEXT, lw=0.8))

    _apply_grafana_style(fig, axes)
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor=_GRAFANA_BG)
    plt.close(fig)

    metadata = {
        "evidence_id": "VE-001",
        "incident_id": INCIDENT_ID,
        "title": "Redis Pool Saturation & Checkout 504 Errors — Grafana Dashboard",
        "description": (
            "Grafana dashboard screenshot showing three panels: "
            "(1) Redis connection pool utilization reaching 100% at 14:02 UTC and "
            "recovering after rollback at 14:22 UTC; "
            "(2) Redis connection acquisition timeouts on auth-service peaking at ~220/min; "
            "(3) Checkout API HTTP 504 errors per minute peaking at ~950, confirming "
            "customer impact from 14:02 to 14:25 UTC. "
            f"Incident: {INCIDENT_ID}"
        ),
        "file_name": "grafana_redis_pool_saturation.png",
        "mime_type": "image/png",
        "captured_at": "2026-10-28T14:30:00Z",
    }
    return buf.getvalue(), metadata


def generate_grafana_screenshot_2() -> tuple[bytes, dict]:
    """
    Screenshot 2: External ingress RPS vs internal auth retry rate.
    Shows external traffic is stable while internal retries spike 15×.
    """
    import random

    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    rng = random.Random(43)

    t_start = T_IMPACT_START - timedelta(minutes=5)
    t_end = T_RECOVERY + timedelta(minutes=5)
    minutes = int((t_end - t_start).total_seconds() / 60)
    times = [t_start + timedelta(minutes=m) for m in range(minutes)]

    normal_retry = 60

    def ingress(t):
        return NORMAL_INGRESS_RPS + rng.randint(-40, 40)

    def retries(t):
        if t < T_IMPACT_START:
            return normal_retry + rng.randint(-5, 5)
        if t < T_ROLLBACK:
            return int(normal_retry * RETRY_MULTIPLIER) + rng.randint(-50, 50)
        if t < T_RECOVERY:
            elapsed = (t - T_ROLLBACK).total_seconds() / 60
            return max(normal_retry, int(normal_retry * RETRY_MULTIPLIER - elapsed * 80))
        return normal_retry + rng.randint(-5, 5)

    ingress_vals = [ingress(t) for t in times]
    retry_vals = [retries(t) for t in times]

    fig, axes = plt.subplots(2, 1, figsize=(19.2, 10.8), sharex=True)
    fig.suptitle(
        f"AegisRCA — Traffic Analysis — Incident {INCIDENT_ID}",
        color=_GRAFANA_TEXT, fontsize=14, fontweight="bold", y=0.98,
    )

    # Panel 1: External ingress
    axes[0].plot(times, ingress_vals, color=_COLORS[3], linewidth=2,
                 label="ingress_requests_per_second (external)")
    axes[0].set_title(
        "External Ingress Traffic — api-gateway  [STABLE — DDoS Ruled Out]",
        fontsize=10
    )
    axes[0].set_ylabel("Requests / second", fontsize=9)
    axes[0].set_ylim(1000, 1500)
    axes[0].fill_between(times, ingress_vals, alpha=0.15, color=_COLORS[3])
    axes[0].axhline(NORMAL_INGRESS_RPS, color=_GRAFANA_TEXT, linestyle=":",
                    linewidth=1, alpha=0.5, label=f"baseline ~{NORMAL_INGRESS_RPS} rps")
    axes[0].legend(loc="upper right", fontsize=8, facecolor=_GRAFANA_PANEL,
                   labelcolor=_GRAFANA_TEXT)

    # Panel 2: Internal retries
    axes[1].plot(times, retry_vals, color=_COLORS[0], linewidth=2,
                 label="internal_retry_per_minute (auth-service)")
    axes[1].set_title(
        f"Internal Auth Retry Rate — auth-service  [SPIKE: ~{RETRY_MULTIPLIER}× baseline]",
        fontsize=10
    )
    axes[1].set_ylabel("Retries / minute", fontsize=9)
    axes[1].set_xlabel("Time (UTC)", fontsize=9)
    axes[1].fill_between(times, retry_vals, alpha=0.15, color=_COLORS[0])
    axes[1].axhline(normal_retry, color=_GRAFANA_TEXT, linestyle=":",
                    linewidth=1, alpha=0.5, label=f"baseline ~{normal_retry}/min")
    axes[1].legend(loc="upper right", fontsize=8, facecolor=_GRAFANA_PANEL,
                   labelcolor=_GRAFANA_TEXT)

    # Event markers
    for ax in axes:
        ax.axvline(T_IMPACT_START, color="#f7da2e", linestyle="--", linewidth=1.2, alpha=0.8)
        ax.axvline(T_ROLLBACK, color="#73bf69", linestyle="--", linewidth=1.2, alpha=0.8)
        ax.axvline(T_RECOVERY, color="#5794f2", linestyle="--", linewidth=1.2, alpha=0.8)

    axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    axes[1].xaxis.set_major_locator(mdates.MinuteLocator(byminute=range(0, 60, 5)))
    fig.autofmt_xdate(rotation=0)

    axes[0].annotate(
        "External traffic flat\n(no DDoS observed)",
        xy=(T_IMPACT_START + timedelta(minutes=5), NORMAL_INGRESS_RPS + 50),
        color="#73bf69", fontsize=9, fontweight="bold",
    )
    axes[1].annotate(
        f"Internal retries spike to {RETRY_MULTIPLIER}× baseline\n(pool exhaustion amplification)",
        xy=(T_IMPACT_START + timedelta(minutes=2), normal_retry * RETRY_MULTIPLIER * 0.85),
        color=_COLORS[0], fontsize=9,
    )

    _apply_grafana_style(fig, axes)
    plt.tight_layout(rect=[0, 0, 1, 0.97])

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=100, facecolor=_GRAFANA_BG)
    plt.close(fig)

    metadata = {
        "evidence_id": "VE-002",
        "incident_id": INCIDENT_ID,
        "title": "External Traffic vs Internal Retry Rate — DDoS Ruled Out",
        "description": (
            "Grafana dashboard screenshot showing two panels: "
            "(1) External ingress traffic remained stable at approximately 1,200 requests/sec "
            "throughout the incident — no DDoS attack observed; "
            "(2) Internal authentication retry rate spiked approximately 15× above the "
            f"{60}/min baseline, caused by Redis connection pool exhaustion on auth-service. "
            "This comparison definitively rules out a DDoS attack as the root cause. "
            f"Incident: {INCIDENT_ID}"
        ),
        "file_name": "grafana_traffic_vs_retries.png",
        "mime_type": "image/png",
        "captured_at": "2026-10-28T14:30:00Z",
    }
    return buf.getvalue(), metadata

