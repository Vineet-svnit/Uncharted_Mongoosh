"use client";

import React from "react";
import { ShieldAlert, FileText, AlertCircle, DollarSign, Clock, HelpCircle, CheckCircle } from "lucide-react";
import { SLAAssessment as SLAAssessmentType } from "@/types/investigation";
import { Badge } from "@/components/ui/Badge";

interface SLAAssessmentProps {
  assessment?: SLAAssessmentType | null;
}

export const SLAAssessment: React.FC<SLAAssessmentProps> = ({ assessment }) => {
  if (!assessment) {
    return (
      <div className="rounded-xl border border-dark-border bg-dark-surface/60 p-5 text-center">
        <HelpCircle className="h-8 w-8 text-slate-muted mx-auto mb-2 opacity-50" />
        <h4 className="text-xs font-semibold text-slate-text">
          No SLA Assessment Available
        </h4>
        <p className="text-[11px] text-slate-muted mt-1">
          No customer contract or downtime criteria evaluated for this incident.
        </p>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "assessed":
        return { label: "Contract Assessed", variant: "success" as const };
      case "unable_to_determine":
        return { label: "Unable to Determine", variant: "warning" as const };
      case "not_applicable":
      default:
        return { label: "Not Applicable", variant: "default" as const };
    }
  };

  const badge = getStatusBadge(assessment.status);

  return (
    <div className="rounded-xl border border-dark-border bg-dark-surface p-4.5 shadow-lg space-y-3.5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-dark-border/60 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-text">
              Customer SLA Assessment
            </h4>
            <p className="text-[11px] text-slate-muted">
              Contractual downtime compliance and financial service credits
            </p>
          </div>
        </div>

        <Badge variant={badge.variant} size="sm" className="font-mono text-[10px]">
          {badge.label}
        </Badge>
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs">
        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60">
          <span className="text-[10px] text-slate-muted font-mono uppercase">
            Customer
          </span>
          <p className="font-semibold text-slate-text mt-0.5 truncate">
            {assessment.customer_id || "Not available"}
          </p>
        </div>

        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60">
          <span className="text-[10px] text-slate-muted font-mono uppercase">
            Downtime
          </span>
          <p className="font-semibold text-slate-text mt-0.5 font-mono">
            {assessment.downtime_minutes !== null && assessment.downtime_minutes !== undefined
              ? `${assessment.downtime_minutes} mins`
              : "Not available"}
          </p>
        </div>

        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60">
          <span className="text-[10px] text-slate-muted font-mono uppercase">
            Formal RCA Required
          </span>
          <div className="mt-0.5 flex items-center gap-1 font-semibold">
            {assessment.rca_required ? (
              <Badge variant="warning" size="sm" className="text-[10px]">
                YES (Mandatory)
              </Badge>
            ) : (
              <Badge variant="outline" size="sm" className="text-[10px]">
                NO
              </Badge>
            )}
          </div>
        </div>

        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60">
          <span className="text-[10px] text-slate-muted font-mono uppercase">
            Financial Credit
          </span>
          <p className="font-semibold text-emerald-400 mt-0.5 font-mono">
            {assessment.credit_percent !== undefined
              ? `${assessment.credit_percent}%`
              : "0%"}
          </p>
        </div>
      </div>

      {/* Explanation / Contract Terms */}
      <div className="p-3 rounded-lg bg-dark-bg/60 border border-dark-border/40 text-xs">
        <span className="text-[10px] font-mono uppercase font-semibold text-slate-muted block mb-1">
          Contractual Ruling &amp; Obligations:
        </span>
        <p className="text-slate-300 leading-relaxed font-sans text-xs">
          {assessment.explanation}
        </p>
      </div>
    </div>
  );
};

