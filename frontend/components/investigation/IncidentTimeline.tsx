"use client";

import React from "react";
import { Clock, ExternalLink, GitCommit, AlertCircle, RefreshCw, CheckCircle2 } from "lucide-react";
import { TimelineEvent } from "@/types/investigation";
import { formatTime, formatDate } from "@/lib/utils";

interface IncidentTimelineProps {
  timeline: TimelineEvent[];
  onEvidenceClick?: (evidenceId: string) => void;
}

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({
  timeline = [],
  onEvidenceClick,
}) => {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="p-6 text-center text-xs text-slate-muted border border-dashed border-dark-border rounded-xl">
        No incident timeline events recorded.
      </div>
    );
  }

  // Sort chronologically ascending
  const sortedEvents = [...timeline].sort((a, b) => {
    return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime();
  });

  const getTimelineIcon = (title: string) => {
    const lower = title.toLowerCase();
    if (lower.includes("deploy") || lower.includes("pr ") || lower.includes("commit")) {
      return GitCommit;
    }
    if (lower.includes("rollback") || lower.includes("revert")) {
      return RefreshCw;
    }
    if (lower.includes("recovery") || lower.includes("confirmed") || lower.includes("resolved")) {
      return CheckCircle2;
    }
    return AlertCircle;
  };

  return (
    <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-gradient-to-b before:from-sky-500 before:via-indigo-500 before:to-emerald-500/80">
      {sortedEvents.map((evt, idx) => {
        const Icon = getTimelineIcon(evt.title);
        const isLast = idx === sortedEvents.length - 1;
        const isFirst = idx === 0;

        return (
          <div key={idx} className="relative group animate-in fade-in duration-150">
            {/* Timeline node marker */}
            <div
              className={`absolute -left-6 top-1 h-5 w-5 rounded-full border-2 bg-dark-bg flex items-center justify-center transition-all ${
                isFirst
                  ? "border-sky-400 text-sky-400 ring-2 ring-sky-400/20"
                  : isLast
                  ? "border-emerald-400 text-emerald-400 ring-2 ring-emerald-400/20"
                  : "border-dark-border text-slate-muted group-hover:border-slate-400 group-hover:text-slate-text"
              }`}
            >
              <Icon className="h-2.5 w-2.5" />
            </div>

            {/* Event Content Card */}
            <div className="rounded-lg border border-dark-border/80 bg-dark-surface p-3 transition-colors hover:border-slate-600 shadow-sm">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="font-mono text-[11px] font-semibold text-accent-primary">
                  {formatTime(evt.timestamp) || formatDate(evt.timestamp)}
                </span>
                <span className="text-[10px] text-slate-muted/60 font-mono">
                  {formatDate(evt.timestamp)}
                </span>
              </div>

              <h4 className="text-xs font-semibold text-slate-text">
                {evt.title}
              </h4>

              <p className="mt-1 text-xs text-slate-300 leading-relaxed font-sans">
                {evt.description}
              </p>

              {/* Associated Evidence IDs */}
              {evt.evidence_ids && evt.evidence_ids.length > 0 && (
                <div className="mt-2.5 pt-2 border-t border-dark-border/40 flex flex-wrap items-center gap-1.5">
                  <span className="text-[10px] text-slate-muted font-mono">
                    Evidence:
                  </span>
                  {evt.evidence_ids.map((evId) => (
                    <button
                      key={evId}
                      onClick={() => onEvidenceClick?.(evId)}
                      className="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-sky-500/10 text-accent-primary border border-sky-500/30 hover:bg-sky-500/20 transition-colors"
                      title={`Inspect evidence ${evId}`}
                    >
                      <span>{evId}</span>
                      <ExternalLink className="h-2.5 w-2.5 opacity-60 ml-0.5" />
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

