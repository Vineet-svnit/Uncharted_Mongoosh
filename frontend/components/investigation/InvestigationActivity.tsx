"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Circle,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  Layers,
  Activity,
  GitCommit,
  Network,
  MessageSquare,
  ShieldAlert,
  Image as ImageIcon,
  FileText,
  Search,
  BookOpen,
  Terminal,
} from "lucide-react";
import { ToolExecution, InvestigationStage } from "@/types/chat";
import { Spinner } from "@/components/ui/Loading";
import { Badge } from "@/components/ui/Badge";

interface InvestigationActivityProps {
  stage: InvestigationStage;
  stageMessage: string;
  toolExecutions: ToolExecution[];
  isStreaming: boolean;
  error?: string | null;
}

const TOOL_ICON_MAP: Record<string, React.FC<{ className?: string }>> = {
  trace_service_dependencies: Network,
  find_recent_deployments: GitCommit,
  query_service_telemetry: Activity,
  search_incident_messages: MessageSquare,
  retrieve_customer_sla: ShieldAlert,
  search_visual_evidence: ImageIcon,
  list_known_incidents: FileText,
  get_incident_details: FileText,
  search_engineering_knowledge: BookOpen,
  investigation_tools: Search,
};

export const InvestigationActivity: React.FC<InvestigationActivityProps> = ({
  stage,
  stageMessage,
  toolExecutions,
  isStreaming,
  error,
}) => {
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null);

  if (!isStreaming && toolExecutions.length === 0 && !error) {
    return null;
  }

  const toggleExpand = (id: string) => {
    setExpandedToolId((prev) => (prev === id ? null : id));
  };

  const getStageHeader = () => {
    switch (stage) {
      case "planning":
        return { label: "Planning Investigation Plan", color: "text-accent-primary" };
      case "investigating":
        return { label: "Investigating Incident Evidence", color: "text-accent-primary" };
      case "verification":
        return { label: "Cross-Checking Evidence & Contradictions", color: "text-indigo-400" };
      case "report_generation":
        return { label: "Synthesizing RCA Report", color: "text-emerald-400" };
      case "completed":
        return { label: "Investigation Completed", color: "text-emerald-400" };
      case "failed":
        return { label: "Investigation Halted", color: "text-rose-400" };
      default:
        return { label: "Investigation In Progress", color: "text-accent-primary" };
    }
  };

  const headerInfo = getStageHeader();

  return (
    <div className="my-4 rounded-xl border border-dark-border bg-dark-surface/90 shadow-xl overflow-hidden animate-in fade-in duration-200">
      {/* Top Banner */}
      <div className="px-4 py-3 bg-dark-surfaceSecondary/60 border-b border-dark-border flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          {isStreaming ? (
            <Spinner size="sm" className="h-4 w-4 text-accent-primary" />
          ) : stage === "completed" ? (
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
          ) : (
            <AlertCircle className="h-4 w-4 text-rose-400" />
          )}

          <div>
            <h4 className={`text-xs font-bold uppercase tracking-wider font-mono ${headerInfo.color}`}>
              {headerInfo.label}
            </h4>
            {stageMessage && (
              <p className="text-[11px] text-slate-muted font-sans mt-0.5">
                {stageMessage}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex h-2 w-2 relative">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-sky-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-sky-500" />
            </span>
          )}
          <Badge variant="outline" size="sm" className="font-mono text-[10px]">
            {toolExecutions.length} tools executed
          </Badge>
        </div>
      </div>

      {/* Execution Pipeline / Steps */}
      <div className="p-3.5 space-y-2">
        {toolExecutions.length === 0 && isStreaming && (
          <div className="flex items-center gap-2 text-xs text-slate-muted py-2 px-1">
            <Spinner size="sm" />
            <span>Formulating multi-step investigation trajectory...</span>
          </div>
        )}

        {toolExecutions.map((item) => {
          const isCompleted = item.status === "completed";
          const isRunning = item.status === "running";
          const isFailed = item.status === "failed";
          const isExpanded = expandedToolId === item.id;
          const ToolIcon = TOOL_ICON_MAP[item.tool] || Terminal;

          return (
            <div
              key={item.id}
              className={`rounded-lg border transition-all ${
                isRunning
                  ? "border-sky-500/40 bg-sky-950/15"
                  : isCompleted
                  ? "border-dark-border/60 bg-dark-bg/60 hover:border-dark-border"
                  : "border-rose-500/30 bg-rose-950/15"
              }`}
            >
              <div
                onClick={() => isCompleted && toggleExpand(item.id)}
                className={`p-2.5 flex items-center justify-between text-xs ${
                  isCompleted ? "cursor-pointer" : ""
                }`}
              >
                <div className="flex items-center gap-2.5 min-w-0">
                  {/* Status Indicator */}
                  {isRunning ? (
                    <Spinner size="sm" className="shrink-0 text-accent-primary" />
                  ) : isCompleted ? (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
                  ) : isFailed ? (
                    <AlertCircle className="h-4 w-4 shrink-0 text-rose-400" />
                  ) : (
                    <Circle className="h-4 w-4 shrink-0 text-slate-600" />
                  )}

                  {/* Tool Icon */}
                  <div className="p-1 rounded bg-dark-surfaceSecondary border border-dark-border/80 text-slate-300 shrink-0">
                    <ToolIcon className="h-3 w-3" />
                  </div>

                  {/* Label and Message */}
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-text truncate">
                        {item.label}
                      </span>
                      <span className="font-mono text-[10px] text-slate-muted/70">
                        ({item.tool})
                      </span>
                    </div>
                    {item.message && (
                      <p className="text-[11px] text-slate-muted truncate mt-0.5">
                        {item.message}
                      </p>
                    )}
                  </div>
                </div>

                {/* Evidence count or Expand chevron */}
                <div className="flex items-center gap-2 shrink-0 ml-2">
                  {item.evidence_count !== undefined && item.evidence_count > 0 && (
                    <Badge variant="info" size="sm" className="text-[10px] font-mono">
                      +{item.evidence_count} evidence
                    </Badge>
                  )}
                  {isCompleted && (
                    <button className="text-slate-muted hover:text-slate-text p-0.5">
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5" />
                      )}
                    </button>
                  )}
                </div>
              </div>

              {/* Collapsible Details */}
              {isExpanded && (
                <div className="px-3 pb-2.5 pt-1 border-t border-dark-border/40 text-[11px] bg-dark-surfaceSecondary/30">
                  {item.summary && (
                    <p className="text-slate-300 font-mono text-[11px] mt-1 bg-dark-bg p-2 rounded border border-dark-border/60">
                      {item.summary}
                    </p>
                  )}
                  <div className="mt-2 flex items-center justify-between text-[10px] text-slate-muted font-mono">
                    <span>Started: {item.started_at ? new Date(item.started_at).toLocaleTimeString() : "N/A"}</span>
                    {item.completed_at && (
                      <span>Done: {new Date(item.completed_at).toLocaleTimeString()}</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}

        {/* Global error banner if investigation failed */}
        {error && (
          <div className="p-3 rounded-lg border border-rose-500/30 bg-rose-950/30 text-rose-300 text-xs flex items-start gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-rose-400 mt-0.5" />
            <div>
              <p className="font-semibold">Investigation Encountered An Error</p>
              <p className="text-[11px] mt-0.5 text-rose-300/80">{error}</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

