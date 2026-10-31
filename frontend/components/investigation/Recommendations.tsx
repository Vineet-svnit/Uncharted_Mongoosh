"use client";

import React from "react";
import { CheckSquare, AlertCircle, ShieldCheck } from "lucide-react";

interface RecommendationsProps {
  recommendations: string[];
}

export const Recommendations: React.FC<RecommendationsProps> = ({
  recommendations = [],
}) => {
  if (!recommendations || recommendations.length === 0) {
    return (
      <div className="p-4 text-center text-xs text-slate-muted border border-dashed border-dark-border rounded-xl">
        No remediation recommendations generated.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-slate-muted">
          <CheckSquare className="h-3.5 w-3.5 text-accent-primary" />
          <span className="font-semibold text-slate-text">
            Recommended Action Items
          </span>
        </div>
        <span className="text-[10px] font-mono text-slate-muted">
          Advisory Only
        </span>
      </div>

      <div className="space-y-2">
        {recommendations.map((rec, idx) => (
          <div
            key={idx}
            className="flex items-start gap-3 p-3 rounded-lg border border-dark-border bg-dark-surface text-xs hover:border-slate-600 transition-colors"
          >
            <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-dark-surfaceSecondary border border-dark-border font-mono text-[11px] font-bold text-accent-primary">
              {idx + 1}
            </span>
            <p className="text-slate-300 leading-relaxed font-sans mt-0.5">
              {rec}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
};

