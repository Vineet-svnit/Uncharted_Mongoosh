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
  CheckCircle2,
  AlertTriangle,
} from "lucide-react";
import { EvidenceItem } from "@/types/investigation";
import { Badge } from "@/components/ui/Badge";
import { formatTime, formatDate } from "@/lib/utils";
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
        return { label: "Supporting Evidence", variant: "success" as const };
      case "contradicting":
        return { label: "Contradicting Evidence", variant: "danger" as const };
      case "contextual":
        return { label: "Contextual Evidence", variant: "info" as const };
      case "unverified":
      default:
        return { label: "Unverified Evidence", variant: "warning" as const };
    }
  };

  const getSourceIcon = (type: string) => {
    switch (type?.toLowerCase()) {
      case "deployment_pr":
      case "pr":
      case "git":
        return GitCommit;
      case "telemetry":
      case "metric":
        return Activity;
      case "slack_message":
      case "chat":
        return MessageSquare;
      case "sla":
      case "contract":
        return ShieldAlert;
      case "visual":
      case "screenshot":
        return ImageIcon;
      default:
        return FileText;
    }
  };

  const badge = getClassificationBadge(evidence.classification);
  const SourceIcon = getSourceIcon(evidence.source_type);
  const citationObj = evidence.citation as any;

  return (
    <div
      onClick={() => onViewDetails(evidence)}
      className="group rounded-xl border border-dark-border bg-dark-surface p-4 hover:border-sky-500/50 hover:bg-dark-surfaceSecondary/60 transition-all cursor-pointer shadow-sm relative overflow-hidden"
    >
      {/* Top row: Evidence ID, classification badge */}
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            size="sm"
            className="font-mono text-[10px] font-bold text-accent-primary bg-sky-500/10 border-sky-500/30"
          >
            {evidence.evidence_id}
          </Badge>
          <div className="flex items-center gap-1 text-[11px] text-slate-muted">
            <SourceIcon className="h-3 w-3" />
            <span className="font-mono">{evidence.source_id}</span>
          </div>
        </div>

        <Badge variant={badge.variant} size="sm" className="text-[10px]">
          {badge.label}
        </Badge>
      </div>

      {/* Title */}
      <h4 className="text-xs font-semibold text-slate-text group-hover:text-sky-300 transition-colors">
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
        </div>

        <span className="flex items-center gap-1 text-accent-primary opacity-0 group-hover:opacity-100 transition-opacity">
          <span>View details</span>
          <ExternalLink className="h-2.5 w-2.5" />
        </span>
      </div>
    </div>
  );
};

