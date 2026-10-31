"use client";

import React from "react";
import { AlertTriangle, ArrowRight, ShieldCheck, Scale, CheckCircle2 } from "lucide-react";
import { EvidenceItem } from "@/types/investigation";
import { Badge } from "@/components/ui/Badge";

interface ContradictionCardProps {
  contradictingEvidence: EvidenceItem[];
  onEvidenceClick?: (evidenceId: string) => void;
}

export const ContradictionCard: React.FC<ContradictionCardProps> = ({
  contradictingEvidence = [],
  onEvidenceClick,
}) => {
  // Do not display the contradiction section when no contradictions are returned
  if (!contradictingEvidence || contradictingEvidence.length === 0) {
    return null;
  }

  return (
    <div className="rounded-xl border border-rose-500/40 bg-rose-950/20 p-4.5 shadow-lg relative overflow-hidden space-y-4">
      {/* Banner */}
      <div className="flex items-center justify-between border-b border-rose-500/20 pb-3">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-rose-500/20 border border-rose-500/40 text-accent-danger">
            <Scale className="h-4 w-4" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider font-mono text-accent-danger">
              Conflicting Evidence Detected
            </h4>
            <p className="text-[11px] text-slate-300">
              Contradictions identified between human hypothesis and verified telemetry
            </p>
          </div>
        </div>
        <Badge variant="danger" size="sm" className="font-mono text-[10px]">
          {contradictingEvidence.length} Conflict{contradictingEvidence.length > 1 ? "s" : ""}
        </Badge>
      </div>

      {/* Side-by-side or stacked contradiction breakdown */}
      <div className="space-y-3">
        {contradictingEvidence.map((ev) => (
          <div
            key={ev.evidence_id}
            className="rounded-lg border border-dark-border/80 bg-dark-bg/90 p-3.5 space-y-3"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
              {/* Human Hypothesis Claim */}
              <div className="p-3 rounded-md bg-dark-surfaceSecondary/60 border border-amber-500/20 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-amber-400">
                    Disputed Hypothesis
                  </span>
                  <span className="font-mono text-[10px] text-slate-muted">
                    {ev.source_id}
                  </span>
                </div>
                <h5 className="font-semibold text-slate-text">{ev.title}</h5>
                <p className="text-[11px] text-slate-300 leading-relaxed font-sans">
                  War room assumption that system failure was driven by external malicious volumetric DDoS traffic.
                </p>
              </div>

              {/* Verified Telemetry / Counterevidence */}
              <div className="p-3 rounded-md bg-dark-surfaceSecondary/60 border border-emerald-500/20 space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-[10px] font-bold uppercase tracking-wider text-emerald-400">
                    Counterevidence (Telemetry)
                  </span>
                  <Badge variant="outline" size="sm" className="font-mono text-[9px] text-sky-400">
                    {ev.evidence_id}
                  </Badge>
                </div>
                <p className="text-[11px] text-slate-300 leading-relaxed font-sans">
                  {ev.content}
                </p>
              </div>
            </div>

            {/* Verdict */}
            <div className="pt-2 border-t border-dark-border/50 flex items-center justify-between text-xs">
              <div className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[11px]">
                <ShieldCheck className="h-4 w-4 shrink-0" />
                <span>
                  Verdict: Available telemetry disproves DDoS hypothesis. Initiating fault was internal connection pool regression.
                </span>
              </div>
              {onEvidenceClick && (
                <button
                  onClick={() => onEvidenceClick(ev.evidence_id)}
                  className="text-[11px] font-mono text-accent-primary hover:underline shrink-0 ml-2"
                >
                  Inspect {ev.evidence_id}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

