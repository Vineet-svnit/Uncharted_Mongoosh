"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  HelpCircle,
  Layers,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { RootCause, AffectedService } from "@/types/investigation";
import { getRootCauseColor } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";

interface RootCauseCardProps {
  rootCause?: RootCause | null;
  affectedServices?: AffectedService[];
}

export const RootCauseCard: React.FC<RootCauseCardProps> = ({
  rootCause,
  affectedServices = [],
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

  if (!rootCause) {
    return (
      <div className="rounded-xl border border-dark-border bg-dark-surface/60 p-5 text-center">
        <HelpCircle className="h-8 w-8 text-slate-muted mx-auto mb-2 opacity-50" />
        <h4 className="text-xs font-semibold text-slate-text">
          Root Cause Not Yet Determined
        </h4>
        <p className="text-[11px] text-slate-muted mt-1">
          Active investigation has not yet isolated the primary initiating fault.
        </p>
      </div>
    );
  }

  const styles = getRootCauseColor(rootCause.status);
  const isExplanationLong = rootCause.explanation.length > 220;

  return (
    <div
      className={`rounded-xl border ${styles.border} ${styles.bg} p-4 shadow-lg relative overflow-hidden transition-all`}
    >
      {/* Background ambient accent */}
      <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-sky-500/5 blur-2xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-lg bg-dark-bg/80 border border-dark-border text-accent-primary shrink-0">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-muted block">
              Root Cause Assessment
            </span>
            <h3 className="text-sm font-bold text-slate-text mt-0.5 leading-snug break-words">
              {rootCause.title}
            </h3>
          </div>
        </div>

        {/* Status Badge & Confidence */}
        <div className="flex items-center gap-1.5 shrink-0">
          <span
            className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold font-mono uppercase tracking-wide border ${styles.badge}`}
          >
            {rootCause.status}
          </span>
          {rootCause.confidence && (
            <Badge variant="outline" size="sm" className="font-mono text-[10px]">
              Conf: {rootCause.confidence}
            </Badge>
          )}
        </div>
      </div>

      {/* Explanation */}
      <div className="bg-dark-bg/60 p-3 rounded-lg border border-dark-border/40 font-sans">
        <p className={`text-xs text-slate-200 leading-relaxed ${!isExpanded && isExplanationLong ? "line-clamp-3" : ""}`}>
          {rootCause.explanation}
        </p>
        {isExplanationLong && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-2 text-[11px] font-mono text-accent-primary hover:underline flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                <span>Show less</span>
                <ChevronUp className="h-3 w-3" />
              </>
            ) : (
              <>
                <span>Read full assessment</span>
                <ChevronDown className="h-3 w-3" />
              </>
            )}
          </button>
        )}
      </div>

      {/* Affected services highlight - full width, responsive, no awkward truncation */}
      {affectedServices.length > 0 && (
        <div className="mt-3.5 pt-3 border-t border-dark-border/40 space-y-2">
          <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-muted">
            <Layers className="h-3 w-3 text-accent-primary" />
            <span>Direct Service Impact ({affectedServices.length})</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-1">
            {affectedServices.map((svc) => (
              <div
                key={svc.service_id}
                className="bg-dark-bg/70 p-2.5 rounded-lg border border-dark-border/60 hover:border-slate-600 transition-colors"
              >
                <div className="flex items-center justify-between gap-1 mb-1">
                  <span className="font-mono font-semibold text-accent-primary text-xs truncate">
                    {svc.service_id}
                  </span>
                </div>
                <p className="text-slate-300 text-[11px] leading-relaxed break-words">
                  {svc.impact}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
