"use client";

import React, { useState } from "react";
import {
  FileText,
  GitCommit,
  Activity,
  MessageSquare,
  ShieldAlert,
  Image as ImageIcon,
  Layers,
  Filter,
} from "lucide-react";
import { EvidenceItem } from "@/types/investigation";
import { EvidenceCard } from "./EvidenceCard";

interface EvidenceListProps {
  supportingEvidence: EvidenceItem[];
  contradictingEvidence: EvidenceItem[];
  citations?: EvidenceItem[];
  onViewDetails: (evidence: EvidenceItem) => void;
}

type CategoryFilter =
  | "all"
  | "deployments"
  | "telemetry"
  | "discussions"
  | "sla"
  | "visual"
  | "contradictions";

export const EvidenceList: React.FC<EvidenceListProps> = ({
  supportingEvidence = [],
  contradictingEvidence = [],
  citations = [],
  onViewDetails,
}) => {
  const [filter, setFilter] = useState<CategoryFilter>("all");

  // Merge unique evidence
  const allMap = new Map<string, EvidenceItem>();
  [...supportingEvidence, ...contradictingEvidence, ...citations].forEach((e) => {
    if (e && e.evidence_id) {
      allMap.set(e.evidence_id, e);
    }
  });
  const allItems = Array.from(allMap.values());

  const filterItem = (item: EvidenceItem): boolean => {
    if (filter === "all") return true;
    if (filter === "contradictions") {
      return item.classification?.toLowerCase() === "contradicting";
    }
    const st = item.source_type?.toLowerCase() || "";
    if (filter === "deployments") {
      return st.includes("deploy") || st.includes("pr") || st.includes("git");
    }
    if (filter === "telemetry") {
      return st.includes("telemetry") || st.includes("metric");
    }
    if (filter === "discussions") {
      return st.includes("slack") || st.includes("message") || st.includes("chat");
    }
    if (filter === "sla") {
      return st.includes("sla") || st.includes("contract");
    }
    if (filter === "visual") {
      return st.includes("visual") || st.includes("screenshot") || !!item.asset_file_id;
    }
    return true;
  };

  const filtered = allItems.filter(filterItem);

  const categories = [
    { id: "all", label: "All Evidence", count: allItems.length },
    {
      id: "deployments",
      label: "Deployments / PRs",
      count: allItems.filter((i) => {
        const s = i.source_type?.toLowerCase() || "";
        return s.includes("deploy") || s.includes("pr") || s.includes("git");
      }).length,
    },
    {
      id: "telemetry",
      label: "Telemetry",
      count: allItems.filter((i) => {
        const s = i.source_type?.toLowerCase() || "";
        return s.includes("telemetry") || s.includes("metric");
      }).length,
    },
    {
      id: "discussions",
      label: "Slack / War Room",
      count: allItems.filter((i) => {
        const s = i.source_type?.toLowerCase() || "";
        return s.includes("slack") || s.includes("message") || s.includes("chat");
      }).length,
    },
    {
      id: "contradictions",
      label: "Contradictions",
      count: contradictingEvidence.length,
    },
    {
      id: "visual",
      label: "Visual / Dashboards",
      count: allItems.filter((i) => i.source_type?.includes("visual") || !!i.asset_file_id).length,
    },
  ];

  return (
    <div className="space-y-4">
      {/* Category Filter Pills */}
      <div className="flex items-center gap-1.5 overflow-x-auto pb-1 no-scrollbar text-xs">
        {categories.map((cat) => {
          const isActive = filter === cat.id;
          return (
            <button
              key={cat.id}
              onClick={() => setFilter(cat.id as CategoryFilter)}
              className={`px-2.5 py-1 rounded-lg font-mono text-[11px] whitespace-nowrap transition-all border ${
                isActive
                  ? "bg-accent-primary/15 border-sky-500/50 text-accent-primary font-semibold"
                  : "bg-dark-surface border-dark-border text-slate-muted hover:border-slate-600 hover:text-slate-text"
              }`}
            >
              <span>{cat.label}</span>
              <span className="ml-1.5 opacity-60">({cat.count})</span>
            </button>
          );
        })}
      </div>

      {/* Grid of Evidence Cards */}
      {filtered.length === 0 ? (
        <div className="p-8 text-center text-xs text-slate-muted border border-dashed border-dark-border rounded-xl">
          No evidence records found in this category.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {filtered.map((item) => (
            <EvidenceCard
              key={item.evidence_id}
              evidence={item}
              onViewDetails={onViewDetails}
            />
          ))}
        </div>
      )}
    </div>
  );
};

