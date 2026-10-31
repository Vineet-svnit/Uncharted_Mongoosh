"use client";

import React, { useState } from "react";
import {
  ShieldAlert,
  Clock,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  FileCheck,
} from "lucide-react";
import { SLAAssessment as SLAAssessmentType } from "@/types/investigation";
import { Badge } from "@/components/ui/Badge";

interface SLAAssessmentProps {
  assessment?: SLAAssessmentType | null;
}

export const SLAAssessment: React.FC<SLAAssessmentProps> = ({ assessment }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);

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
  const isExplanationLong = assessment.explanation.length > 200;

  return (
    <div className="rounded-xl border border-dark-border bg-dark-surface p-4 shadow-lg space-y-3.5">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-dark-border/60 pb-3 gap-2">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-lg bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 shrink-0">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-slate-text">
              Customer SLA Assessment
            </h4>
            <p className="text-[11px] text-slate-muted truncate">
              Contractual downtime compliance and financial service credits
            </p>
          </div>
        </div>

        <Badge variant={badge.variant} size="sm" className="font-mono text-[10px] shrink-0">
          {badge.label}
        </Badge>
      </div>

      {/* Metrics Grid - responsive 2 or 4 columns */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
        {/* 1. Customer */}
        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60 flex flex-col justify-between">
          <span className="text-[10px] text-slate-muted font-mono uppercase tracking-wide">
            Customer
          </span>
          <p className="font-semibold text-slate-text mt-1 text-xs truncate" title={assessment.customer_id || "acme-corp"}>
            {assessment.customer_id || "acme-corp"}
          </p>
        </div>

        {/* 2. Downtime */}
        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60 flex flex-col justify-between">
          <span className="text-[10px] text-slate-muted font-mono uppercase tracking-wide">
            Downtime
          </span>
          <p className="font-bold text-slate-text mt-1 font-mono text-xs text-amber-300">
            {assessment.downtime_minutes !== null && assessment.downtime_minutes !== undefined
              ? `${assessment.downtime_minutes} mins`
              : "Not available"}
          </p>
        </div>

        {/* 3. Formal RCA Required */}
        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60 flex flex-col justify-between">
          <span className="text-[10px] text-slate-muted font-mono uppercase tracking-wide">
            Formal RCA
          </span>
          <div className="mt-1">
            {assessment.rca_required ? (
              <Badge variant="warning" size="sm" className="text-[10px] font-bold">
                Mandatory
              </Badge>
            ) : (
              <Badge variant="outline" size="sm" className="text-[10px]">
                Not Required
              </Badge>
            )}
          </div>
        </div>

        {/* 4. Financial Credit */}
        <div className="p-2.5 rounded-lg bg-dark-surfaceSecondary/60 border border-dark-border/60 flex flex-col justify-between">
          <span className="text-[10px] text-slate-muted font-mono uppercase tracking-wide">
            Financial Credit
          </span>
          <p className="font-bold text-emerald-400 mt-1 font-mono text-xs">
            {assessment.credit_percent !== undefined
              ? `${assessment.credit_percent}%`
              : "0%"}
          </p>
        </div>
      </div>

      {/* Contractual Ruling & Obligations */}
      <div className="p-3 rounded-lg bg-dark-bg/60 border border-dark-border/50 text-xs">
        <div className="flex items-center gap-1.5 text-[10px] font-mono uppercase font-semibold text-slate-muted mb-1.5">
          <FileCheck className="h-3.5 w-3.5 text-indigo-400" />
          <span>Contractual Ruling &amp; Obligations</span>
        </div>
        <p className={`text-slate-300 leading-relaxed font-sans text-xs ${!isExpanded && isExplanationLong ? "line-clamp-3" : ""}`}>
          {assessment.explanation}
        </p>
        {isExplanationLong && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="mt-1.5 text-[11px] font-mono text-indigo-400 hover:underline flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                <span>Show less</span>
                <ChevronUp className="h-3 w-3" />
              </>
            ) : (
              <>
                <span>Read full ruling</span>
                <ChevronDown className="h-3 w-3" />
              </>
            )}
          </button>
        )}
      </div>
    </div>
  );
};
