"use client";

import React from "react";
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  HelpCircle,
  Activity,
  Layers,
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

  return (
    <div
      className={`rounded-xl border ${styles.border} ${styles.bg} p-4.5 shadow-lg relative overflow-hidden transition-all`}
    >
      {/* Background ambient accent */}
      <div className="absolute -right-10 -top-10 h-32 w-32 rounded-full bg-sky-500/5 blur-2xl pointer-events-none" />

      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-dark-bg/80 border border-dark-border text-accent-primary">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider text-slate-muted">
              Root Cause Assessment
            </span>
            <h3 className="text-sm font-bold text-slate-text mt-0.5 leading-snug">
              {rootCause.title}
            </h3>
          </div>
        </div>

        {/* Status Badge */}
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
      <p className="text-xs text-slate-300 leading-relaxed bg-dark-bg/50 p-3 rounded-lg border border-dark-border/40 font-sans">
        {rootCause.explanation}
      </p>

      {/* Affected services highlight */}
      {affectedServices.length > 0 && (
        <div className="mt-3 pt-3 border-t border-dark-border/40 space-y-1.5">
          <div className="flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider text-slate-muted">
            <Layers className="h-3 w-3" />
            <span>Direct Service Impact</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-1">
            {affectedServices.slice(0, 2).map((svc) => (
              <div
                key={svc.service_id}
                className="bg-dark-bg/60 p-2 rounded border border-dark-border/50 text-[11px]"
              >
                <div className="font-mono font-semibold text-accent-primary truncate">
                  {svc.service_id}
                </div>
                <div className="text-slate-muted truncate text-[10px] mt-0.5">
                  {svc.impact}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

