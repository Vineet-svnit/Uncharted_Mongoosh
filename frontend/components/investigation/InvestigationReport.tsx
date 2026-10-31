"use client";

import React, { useState } from "react";
import {
  FileText,
  Clock,
  Network,
  Layers,
  BarChart2,
  ZoomIn,
  Copy,
  Check,
  FileCode,
  Sliders,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  InvestigationResult,
  EvidenceItem,
} from "@/types/investigation";
import { RootCauseCard } from "./RootCauseCard";
import { IncidentTimeline } from "./IncidentTimeline";
import { ServiceDependencyGraph } from "./ServiceDependencyGraph";
import { EvidenceList } from "./EvidenceList";
import { ContradictionCard } from "./ContradictionCard";
import { SLAAssessment } from "./SLAAssessment";
import { Recommendations } from "./Recommendations";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Drawer } from "@/components/ui/Drawer";
import { getEvidenceAssetUrl } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
} from "recharts";

interface InvestigationReportProps {
  result: InvestigationResult;
  inspectedEvidence: EvidenceItem | null;
  onCloseInspectedEvidence: () => void;
  onSelectEvidence: (evidence: EvidenceItem) => void;
  inspectorWidth?: number;
  onWidthChange?: (width: number) => void;
}

export const InvestigationReport: React.FC<InvestigationReportProps> = ({
  result,
  inspectedEvidence,
  onCloseInspectedEvidence,
  onSelectEvidence,
  inspectorWidth = 520,
  onWidthChange,
}) => {
  const [activeTab, setActiveTab] = useState<
    "overview" | "timeline" | "topology" | "evidence" | "telemetry"
  >("overview");

  const [isSummaryExpanded, setIsSummaryExpanded] = useState<boolean>(false);

  // Zoomed visual image modal
  const [zoomedImage, setZoomedImage] = useState<{
    url: string;
    title: string;
    description: string;
  } | null>(null);

  const [copiedSnippet, setCopiedSnippet] = useState<boolean>(false);

  const handleCopySnippet = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedSnippet(true);
    setTimeout(() => setCopiedSnippet(false), 2000);
  };

  const hasContradictions =
    result.contradicting_evidence && result.contradicting_evidence.length > 0;

  const hasTelemetrySeries =
    result.telemetry_series && result.telemetry_series.length > 0;

  const findEvidenceById = (evId: string) => {
    const all = [
      ...(result.supporting_evidence || []),
      ...(result.contradicting_evidence || []),
      ...((result.citations as EvidenceItem[]) || []),
    ];
    const found = all.find((e) => e?.evidence_id === evId);
    if (found) {
      onSelectEvidence(found);
    }
  };

  const isSummaryLong = (result.summary || "").length > 180;

  return (
    <div className="flex flex-col h-full bg-dark-surface overflow-hidden">
      {/* Top Inspector Header */}
      <div className="p-4 border-b border-dark-border bg-dark-surfaceSecondary/40 shrink-0 space-y-3">
        {/* Title, Incident ID & Status Badges */}
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs font-mono font-bold uppercase tracking-wider text-accent-primary">
              Investigation Inspector
            </span>
            {result.incident_id && (
              <Badge variant="warning" size="sm" className="font-mono text-[10px]">
                {result.incident_id}
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Badge
              variant={
                result.investigation_status === "completed"
                  ? "success"
                  : result.investigation_status === "failed"
                  ? "danger"
                  : "warning"
              }
              size="sm"
              className="font-mono text-[10px] uppercase font-bold"
            >
              {result.investigation_status}
            </Badge>
          </div>
        </div>

        {/* Width Slider & Quick S/M/L Presets */}
        {onWidthChange && (
          <div className="flex items-center justify-between gap-2 pt-1 pb-1 border-y border-dark-border/40 text-xs text-slate-muted">
            <div className="flex items-center gap-2">
              <Sliders className="h-3.5 w-3.5 text-accent-primary shrink-0" />
              <span className="text-[10px] font-mono shrink-0">
                Width: {inspectorWidth}px
              </span>
              <input
                type="range"
                min={380}
                max={920}
                step={20}
                value={inspectorWidth}
                onChange={(e) => onWidthChange(Number(e.target.value))}
                className="w-20 sm:w-28 h-1.5 bg-dark-border rounded-lg appearance-none cursor-pointer accent-sky-400"
                title="Slide to adjust inspector width"
              />
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={() => onWidthChange(420)}
                className={`px-1.5 py-0.5 text-[9px] font-mono rounded border transition-colors ${
                  inspectorWidth <= 460
                    ? "border-sky-500 bg-sky-500/20 text-sky-300 font-bold"
                    : "border-dark-border text-slate-muted hover:text-slate-text"
                }`}
                title="Compact (420px)"
              >
                S
              </button>
              <button
                onClick={() => onWidthChange(580)}
                className={`px-1.5 py-0.5 text-[9px] font-mono rounded border transition-colors ${
                  inspectorWidth > 460 && inspectorWidth <= 680
                    ? "border-sky-500 bg-sky-500/20 text-sky-300 font-bold"
                    : "border-dark-border text-slate-muted hover:text-slate-text"
                }`}
                title="Balanced (580px)"
              >
                M
              </button>
              <button
                onClick={() => onWidthChange(800)}
                className={`px-1.5 py-0.5 text-[9px] font-mono rounded border transition-colors ${
                  inspectorWidth > 680
                    ? "border-sky-500 bg-sky-500/20 text-sky-300 font-bold"
                    : "border-dark-border text-slate-muted hover:text-slate-text"
                }`}
                title="Wide (800px)"
              >
                L
              </button>
            </div>
          </div>
        )}

        {/* Executive Summary */}
        <div>
          <p className={`text-xs text-slate-300 leading-relaxed font-sans ${!isSummaryExpanded && isSummaryLong ? "line-clamp-2" : ""}`}>
            {result.summary}
          </p>
          {isSummaryLong && (
            <button
              onClick={() => setIsSummaryExpanded(!isSummaryExpanded)}
              className="mt-1 text-[11px] font-mono text-accent-primary hover:underline flex items-center gap-1"
            >
              {isSummaryExpanded ? (
                <>
                  <span>Show less</span>
                  <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  <span>Read full summary</span>
                  <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          )}
        </div>

        {/* Tab Navigation Bar */}
        <div className="flex items-center gap-1.5 pt-1 overflow-x-auto no-scrollbar text-xs">
          <button
            onClick={() => setActiveTab("overview")}
            className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0 ${
              activeTab === "overview"
                ? "bg-dark-surface text-accent-primary border border-dark-border shadow-xs font-semibold"
                : "text-slate-muted hover:text-slate-text hover:bg-dark-surface/50"
            }`}
          >
            <FileText className="h-3.5 w-3.5" />
            <span>Overview</span>
          </button>

          <button
            onClick={() => setActiveTab("timeline")}
            className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0 ${
              activeTab === "timeline"
                ? "bg-dark-surface text-accent-primary border border-dark-border shadow-xs font-semibold"
                : "text-slate-muted hover:text-slate-text hover:bg-dark-surface/50"
            }`}
          >
            <Clock className="h-3.5 w-3.5" />
            <span>Timeline</span>
            <span className="px-1.5 py-0.2 rounded-full bg-dark-bg border border-dark-border text-[10px] font-mono">
              {result.timeline?.length || 0}
            </span>
          </button>

          <button
            onClick={() => setActiveTab("topology")}
            className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0 ${
              activeTab === "topology"
                ? "bg-dark-surface text-accent-primary border border-dark-border shadow-xs font-semibold"
                : "text-slate-muted hover:text-slate-text hover:bg-dark-surface/50"
            }`}
          >
            <Network className="h-3.5 w-3.5" />
            <span>Topology</span>
          </button>

          <button
            onClick={() => setActiveTab("evidence")}
            className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0 ${
              activeTab === "evidence"
                ? "bg-dark-surface text-accent-primary border border-dark-border shadow-xs font-semibold"
                : "text-slate-muted hover:text-slate-text hover:bg-dark-surface/50"
            }`}
          >
            <Layers className="h-3.5 w-3.5" />
            <span>Evidence</span>
            <span className="px-1.5 py-0.2 rounded-full bg-dark-bg border border-dark-border text-[10px] font-mono">
              {(result.supporting_evidence?.length || 0) +
                (result.contradicting_evidence?.length || 0)}
            </span>
          </button>

          {hasTelemetrySeries && (
            <button
              onClick={() => setActiveTab("telemetry")}
              className={`px-3 py-1.5 rounded-lg font-medium text-xs transition-colors flex items-center gap-1.5 whitespace-nowrap shrink-0 ${
                activeTab === "telemetry"
                  ? "bg-dark-surface text-accent-primary border border-dark-border shadow-xs font-semibold"
                  : "text-slate-muted hover:text-slate-text hover:bg-dark-surface/50"
              }`}
            >
              <BarChart2 className="h-3.5 w-3.5" />
              <span>Telemetry</span>
            </button>
          )}
        </div>
      </div>

      {/* Tab Panels */}
      <div className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-5">
        {/* TAB 1: OVERVIEW */}
        {activeTab === "overview" && (
          <div className="space-y-5">
            {/* 1. Root Cause Card */}
            <RootCauseCard
              rootCause={result.root_cause}
              affectedServices={result.affected_services}
            />

            {/* 2. Contradiction Detector */}
            {hasContradictions && (
              <ContradictionCard
                contradictingEvidence={result.contradicting_evidence}
                onEvidenceClick={findEvidenceById}
              />
            )}

            {/* 3. SLA Assessment */}
            {result.sla_assessment && (
              <SLAAssessment assessment={result.sla_assessment} />
            )}

            {/* 4. Recommendations */}
            {result.recommendations && result.recommendations.length > 0 && (
              <Recommendations recommendations={result.recommendations} />
            )}
          </div>
        )}

        {/* TAB 2: TIMELINE */}
        {activeTab === "timeline" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-muted mb-2">
              <span className="font-semibold text-slate-text">Chronological Events</span>
              <span className="font-mono text-[10px]">All times in UTC</span>
            </div>
            <IncidentTimeline
              timeline={result.timeline}
              onEvidenceClick={findEvidenceById}
            />
          </div>
        )}

        {/* TAB 3: TOPOLOGY */}
        {activeTab === "topology" && (
          <ServiceDependencyGraph
            serviceGraph={result.service_graph}
            affectedServices={result.affected_services}
          />
        )}

        {/* TAB 4: EVIDENCE */}
        {activeTab === "evidence" && (
          <EvidenceList
            supportingEvidence={result.supporting_evidence}
            contradictingEvidence={result.contradicting_evidence}
            citations={result.citations as EvidenceItem[]}
            onViewDetails={(ev) => onSelectEvidence(ev)}
          />
        )}

        {/* TAB 5: TELEMETRY (Recharts) */}
        {activeTab === "telemetry" && hasTelemetrySeries && (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-slate-muted">
              <span className="font-semibold text-slate-text">
                Metric Telemetry Correlation
              </span>
              <span className="font-mono text-[10px]">UTC Time Series</span>
            </div>

            {/* Redis Pool Saturation & 504 Error Rate Chart */}
            <div className="p-4 rounded-xl border border-dark-border bg-dark-bg/80">
              <h5 className="text-xs font-semibold text-slate-text mb-1">
                Redis Pool Saturation vs 504 Spikes
              </h5>
              <p className="text-[11px] text-slate-muted mb-4">
                Pool pegged at 100% (50/50 connections) directly drove 92.4% Checkout 504 errors.
              </p>

              <div className="h-56 w-full text-xs">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.telemetry_series || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#293750" />
                    <XAxis dataKey="timestamp" stroke="#94A3B8" fontSize={10} />
                    <YAxis stroke="#94A3B8" fontSize={10} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#151F33",
                        borderColor: "#293750",
                        borderRadius: "8px",
                        fontSize: "11px",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "11px" }} />
                    <Line
                      type="monotone"
                      dataKey="redis_utilization"
                      name="Redis Pool Saturation %"
                      stroke="#FB7185"
                      strokeWidth={2}
                      dot={false}
                    />
                    <Line
                      type="monotone"
                      dataKey="checkout_504_pct"
                      name="Checkout 504 Rate %"
                      stroke="#FBBF24"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Edge Ingress vs Internal Retries Chart (DDoS Refutation) */}
            <div className="p-4 rounded-xl border border-dark-border bg-dark-bg/80">
              <h5 className="text-xs font-semibold text-slate-text mb-1">
                Edge Ingress Traffic vs Internal Retry Multiplier
              </h5>
              <p className="text-[11px] text-slate-muted mb-4">
                Ingress remained flat (1,210 RPS); internal retry storm surged 15x.
              </p>

              <div className="h-56 w-full text-xs">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={result.telemetry_series || []}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#293750" />
                    <XAxis dataKey="timestamp" stroke="#94A3B8" fontSize={10} />
                    <YAxis stroke="#94A3B8" fontSize={10} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: "#151F33",
                        borderColor: "#293750",
                        borderRadius: "8px",
                        fontSize: "11px",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: "11px" }} />
                    <Line
                      type="monotone"
                      dataKey="internal_retries"
                      name="Internal Retry Multiplier (x)"
                      stroke="#818CF8"
                      strokeWidth={2}
                    />
                    <Line
                      type="monotone"
                      dataKey="ingress_rps"
                      name="Edge Ingress RPS"
                      stroke="#38BDF8"
                      strokeWidth={2}
                      dot={false}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* EVIDENCE DETAILS DRAWER */}
      <Drawer
        isOpen={!!inspectedEvidence}
        onClose={onCloseInspectedEvidence}
        title={inspectedEvidence?.title || "Evidence Details"}
        description={`Evidence Identifier: ${inspectedEvidence?.evidence_id || "N/A"}`}
        width="lg"
      >
        {inspectedEvidence && (
          <div className="space-y-4 text-xs">
            {/* Meta tags */}
            <div className="flex flex-wrap items-center gap-2 pb-3 border-b border-dark-border">
              <Badge variant="info" size="sm" className="font-mono">
                {inspectedEvidence.evidence_id}
              </Badge>
              <Badge variant="outline" size="sm" className="font-mono">
                {inspectedEvidence.source_type}
              </Badge>
              <Badge
                variant={
                  inspectedEvidence.classification === "supporting"
                    ? "success"
                    : inspectedEvidence.classification === "contradicting"
                    ? "danger"
                    : "default"
                }
                size="sm"
              >
                {inspectedEvidence.classification || "Supporting"}
              </Badge>
              {inspectedEvidence.retrieval_method && (
                <span className="text-[10px] font-mono text-slate-muted">
                  Tool: {inspectedEvidence.retrieval_method}
                </span>
              )}
            </div>

            {/* Visual Screenshot / Asset if available */}
            {inspectedEvidence.asset_file_id && (
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-slate-muted text-[11px]">
                  <span>Visual Evidence (MongoDB GridFS Asset)</span>
                  <button
                    onClick={() =>
                      setZoomedImage({
                        url: getEvidenceAssetUrl(inspectedEvidence.asset_file_id!),
                        title: inspectedEvidence.title,
                        description: inspectedEvidence.content,
                      })
                    }
                    className="flex items-center gap-1 text-accent-primary hover:underline text-[11px]"
                  >
                    <ZoomIn className="h-3 w-3" />
                    <span>Zoom full size</span>
                  </button>
                </div>
                <div
                  onClick={() =>
                    setZoomedImage({
                      url: getEvidenceAssetUrl(inspectedEvidence.asset_file_id!),
                      title: inspectedEvidence.title,
                      description: inspectedEvidence.content,
                    })
                  }
                  className="rounded-xl overflow-hidden border border-dark-border cursor-pointer group relative bg-black/40"
                >
                  <img
                    src={getEvidenceAssetUrl(inspectedEvidence.asset_file_id)}
                    alt={inspectedEvidence.title}
                    className="w-full h-auto object-cover group-hover:scale-[1.01] transition-transform"
                  />
                  <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity">
                    <span className="px-3 py-1.5 rounded-lg bg-dark-surface/90 text-slate-text text-xs font-semibold flex items-center gap-1.5 shadow-lg border border-dark-border">
                      <ZoomIn className="h-3.5 w-3.5 text-accent-primary" />
                      <span>Click to enlarge</span>
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Full Content */}
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono uppercase font-semibold text-slate-muted">
                  Raw Content / Telemetry Extract
                </span>
                <button
                  onClick={() => handleCopySnippet(inspectedEvidence.content)}
                  className="flex items-center gap-1 text-[10px] text-slate-muted hover:text-slate-text"
                >
                  {copiedSnippet ? (
                    <Check className="h-3 w-3 text-emerald-400" />
                  ) : (
                    <Copy className="h-3 w-3" />
                  )}
                  <span>{copiedSnippet ? "Copied" : "Copy"}</span>
                </button>
              </div>
              <div className="p-3 rounded-lg bg-dark-bg/90 border border-dark-border text-slate-200 font-mono text-xs leading-relaxed whitespace-pre-wrap">
                {inspectedEvidence.content}
              </div>
            </div>

            {/* Citation Details */}
            {inspectedEvidence.citation && (
              <div className="p-3 rounded-lg bg-dark-surfaceSecondary/50 border border-dark-border space-y-2">
                <div className="flex items-center gap-1.5 text-slate-text font-semibold">
                  <FileCode className="h-3.5 w-3.5 text-accent-primary" />
                  <span>Verified Source Citation</span>
                </div>
                <div className="grid grid-cols-2 gap-2 font-mono text-[11px] text-slate-300">
                  <div>
                    <span className="text-slate-muted">File: </span>
                    <span className="text-accent-primary">
                      {(inspectedEvidence.citation as any).file_name || "N/A"}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-muted">Lines: </span>
                    <span>
                      {(inspectedEvidence.citation as any).line_start !== undefined
                        ? `L${(inspectedEvidence.citation as any).line_start} - L${
                            (inspectedEvidence.citation as any).line_end
                          }`
                        : "Full Document"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Metadata properties */}
            <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-muted pt-2 border-t border-dark-border/40">
              <div>
                <span>Service Target: </span>
                <span className="font-mono text-slate-text">
                  {inspectedEvidence.service_id || "Global"}
                </span>
              </div>
              <div>
                <span>Timestamp: </span>
                <span className="font-mono text-slate-text">
                  {inspectedEvidence.timestamp
                    ? formatDate(inspectedEvidence.timestamp)
                    : "Not specified"}
                </span>
              </div>
            </div>
          </div>
        )}
      </Drawer>

      {/* FULL-SIZE ZOOM MODAL FOR SCREENSHOT EVIDENCE */}
      <Modal
        isOpen={!!zoomedImage}
        onClose={() => setZoomedImage(null)}
        title={zoomedImage?.title}
        description={zoomedImage?.description}
        maxWidth="4xl"
      >
        {zoomedImage && (
          <div className="space-y-4">
            <div className="rounded-xl overflow-hidden border border-dark-border bg-black max-h-[70vh] flex items-center justify-center">
              <img
                src={zoomedImage.url}
                alt={zoomedImage.title}
                className="w-full h-auto object-contain"
              />
            </div>
            <div className="flex justify-end">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setZoomedImage(null)}
              >
                Close Fullscreen
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
