"use client";

import React from "react";
import {
  FileText,
  GitCommit,
  Activity,
  MessageSquare,
  ShieldAlert,
  Image as ImageIcon,
  ExternalLink,
  Clock,
  Layers,
  BookOpen,
  FileSearch,
} from "lucide-react";
import { EvidenceItem } from "@/types/investigation";
import { Badge } from "@/components/ui/Badge";
import { formatTime } from "@/lib/utils";
import { getEvidenceAssetUrl } from "@/lib/api";

interface EvidenceCardProps {
  evidence: EvidenceItem;
  onViewDetails: (evidence: EvidenceItem) => void;
}

export const EvidenceCard: React.FC<EvidenceCardProps> = ({
  evidence,
  onViewDetails,
}) => {
  const getClassificationBadge = (classification?: string) => {
    switch (classification?.toLowerCase()) {
      case "supporting":
        return { label: "Supporting", variant: "success" as const };
      case "contradicting":
        return { label: "Contradicting", variant: "danger" as const };
      case "contextual":
        return { label: "Contextual", variant: "info" as const };
      case "unverified":
        return { label: "Contextual / Speculation", variant: "warning" as const };
      default:
        return { label: "Supporting", variant: "success" as const };
    }
  };

  const getSourceIcon = (type: string) => {
    const t = type?.toLowerCase() || "";
    if (t.includes("deploy") || t.includes("pr") || t.includes("git")) return GitCommit;
    if (t.includes("telemetry") || t.includes("metric")) return Activity;
    if (t.includes("slack") || t.includes("message") || t.includes("chat")) return MessageSquare;
    if (t.includes("sla") || t.includes("contract")) return ShieldAlert;
    if (t.includes("grafana") || t.includes("screenshot") || t.includes("visual")) return ImageIcon;
    if (t.includes("runbook") || t.includes("postmortem") || t.includes("knowledge")) return BookOpen;
    if (t.includes("incident_record") || t.includes("topology")) return FileSearch;
    return FileText;
  };

  const badge = getClassificationBadge(evidence.classification);
  const SourceIcon = getSourceIcon(evidence.source_type);
  const citationObj = evidence.citation as any;

  // PDF link for SLA/contract source types with page info
  const pdfPage = citationObj?.page;
  const pdfFileId = citationObj?.pdf_file_id;
  const hasPdfLink = pdfFileId && (
    evidence.source_type === "sla_text" ||
    evidence.source_type === "sla" ||
    evidence.source_type === "contract" ||
    evidence.source_type === "pdf_contract"
  );

  return (
    <div
      onClick={() => onViewDetails(evidence)}
      className="group rounded-xl border border-dark-border bg-dark-surface p-4 hover:border-sky-500/50 hover:bg-dark-surfaceSecondary/60 transition-all cursor-pointer shadow-sm relative overflow-hidden"
    >
      {/* Top row: Evidence ID, source ID, classification badge */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <Badge
            variant="outline"
            size="sm"
            className="font-mono text-[10px] font-bold text-accent-primary bg-sky-500/10 border-sky-500/30 shrink-0"
          >
            {evidence.evidence_id}
          </Badge>
          <div className="flex items-center gap-1 text-[11px] text-slate-muted min-w-0">
            <SourceIcon className="h-3 w-3 shrink-0" />
            <span className="font-mono truncate">{evidence.source_id}</span>
          </div>
        </div>

        <div className="flex items-center gap-1.5 shrink-0">
          {evidence.source_status && (
            <Badge
              variant={evidence.source_status === "verified" ? "success" : "danger"}
              size="sm"
              className="text-[9px] font-mono px-1.5 py-0"
            >
              {evidence.source_status === "verified" ? "✓ Verified" : "Unavailable"}
            </Badge>
          )}
          {evidence.claim_support && evidence.claim_support !== "supported" && (
            <Badge
              variant={
                evidence.claim_support === "contradicted"
                  ? "danger"
                  : evidence.claim_support === "partially_supported"
                  ? "info"
                  : "warning"
              }
              size="sm"
              className="text-[9px] font-mono px-1.5 py-0"
            >
              {evidence.claim_support === "contradicted"
                ? "Contradicted"
                : evidence.claim_support === "partially_supported"
                ? "Partial"
                : "Insufficient"}
            </Badge>
          )}
          <Badge variant={badge.variant} size="sm" className="text-[10px]">
            {badge.label}
          </Badge>
        </div>
      </div>

      {/* Title */}
      <h4 className="text-xs font-semibold text-slate-text group-hover:text-sky-300 transition-colors leading-snug">
        {evidence.title}
      </h4>

      {/* Snippet */}
      <p className="mt-1.5 text-xs text-slate-400 line-clamp-2 leading-relaxed">
        {evidence.content}
      </p>

      {/* Visual Asset Thumbnail Preview if present */}
      {evidence.asset_file_id && (
        <div className="mt-2.5 rounded-lg overflow-hidden border border-dark-border bg-black/40 relative aspect-video flex items-center justify-center">
          <img
            src={getEvidenceAssetUrl(evidence.asset_file_id)}
            alt={evidence.title}
            className="w-full h-full object-cover opacity-85 group-hover:opacity-100 transition-opacity"
            loading="lazy"
          />
          <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/70 text-[9px] font-mono text-slate-300 flex items-center gap-1">
            <ImageIcon className="h-2.5 w-2.5 text-sky-400" />
            <span>Screenshot</span>
          </div>
        </div>
      )}

      {/* PDF contract provenance info (no external link for safe deployment) */}
      {hasPdfLink && (
        <div className="mt-2 inline-flex items-center gap-1.5 text-[10px] font-mono text-slate-400 bg-dark-surfaceSecondary/80 px-2 py-0.5 rounded border border-dark-border/60">
          <ShieldAlert className="h-2.5 w-2.5 text-sky-400" />
          <span>SLA Reference: Page {pdfPage || "N/A"}{citationObj?.clause ? ` (Clause ${citationObj.clause})` : ""}</span>
        </div>
      )}

      {/* Metadata footer */}
      <div className="mt-3 pt-2.5 border-t border-dark-border/40 flex items-center justify-between text-[10px] font-mono text-slate-muted">
        <div className="flex items-center gap-2">
          {evidence.service_id && (
            <span className="flex items-center gap-1">
              <Layers className="h-2.5 w-2.5" />
              {evidence.service_id}
            </span>
          )}
          {evidence.timestamp && (
            <span className="flex items-center gap-1">
              <Clock className="h-2.5 w-2.5" />
              {formatTime(evidence.timestamp)}
            </span>
          )}
          {citationObj?.page && !hasPdfLink && (
            <span className="text-slate-600">p.{citationObj.page}</span>
          )}
        </div>

        <span className="flex items-center gap-1 text-accent-primary opacity-0 group-hover:opacity-100 transition-opacity">
          <span>View details</span>
          <ExternalLink className="h-2.5 w-2.5" />
        </span>
      </div>
    </div>
  );
};
