"use client";

import React from "react";
import { Network, Server, ArrowDown, ArrowRight, ShieldCheck, AlertCircle } from "lucide-react";
import { ServiceGraph, AffectedService } from "@/types/investigation";
import { Badge } from "@/components/ui/Badge";

interface ServiceDependencyGraphProps {
  serviceGraph?: ServiceGraph | null;
  affectedServices?: AffectedService[];
}

export const ServiceDependencyGraph: React.FC<ServiceDependencyGraphProps> = ({
  serviceGraph,
  affectedServices = [],
}) => {
  // Check if graph edges are present
  const hasEdges = serviceGraph?.edges && serviceGraph.edges.length > 0;
  const nodes = serviceGraph?.nodes || [];

  const getNodeBadge = (status: string) => {
    switch (status) {
      case "root_cause":
        return {
          bg: "bg-rose-950/40 border-rose-500/70 text-rose-300 ring-2 ring-rose-500/20",
          tag: "Root Cause / Regressed",
          tagColor: "danger" as const,
        };
      case "failing":
        return {
          bg: "bg-amber-950/40 border-amber-500/70 text-amber-300 ring-2 ring-amber-500/20",
          tag: "Failing (504s)",
          tagColor: "warning" as const,
        };
      case "impacted":
        return {
          bg: "bg-sky-950/40 border-sky-500/60 text-sky-300",
          tag: "Saturated / Impacted",
          tagColor: "info" as const,
        };
      case "healthy":
      default:
        return {
          bg: "bg-emerald-950/20 border-emerald-500/40 text-emerald-300",
          tag: "Healthy",
          tagColor: "success" as const,
        };
    }
  };

  // If backend provided structured dependency graph with edges
  if (hasEdges && nodes.length > 0) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5 text-xs text-slate-muted">
            <Network className="h-3.5 w-3.5 text-accent-primary" />
            <span className="font-semibold text-slate-text">Topology Graph</span>
          </div>
          <span className="text-[10px] font-mono text-slate-muted">
            {nodes.length} Nodes • {serviceGraph?.edges.length} Edges
          </span>
        </div>

        {/* Visual Flow Representation */}
        <div className="p-4 rounded-xl border border-dark-border bg-dark-bg/80 flex flex-col items-center gap-3 relative overflow-hidden">
          {nodes.map((node, idx) => {
            const badge = getNodeBadge(node.status);
            const edgeFromThis = serviceGraph?.edges.find((e) => e.from === node.id);

            return (
              <React.Fragment key={node.id}>
                {/* Node Box */}
                <div
                  className={`w-full max-w-sm rounded-lg border p-3.5 transition-all shadow-md ${badge.bg}`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <Server className="h-4 w-4 shrink-0" />
                      <span className="font-mono text-xs font-bold tracking-tight text-slate-text">
                        {node.label || node.id}
                      </span>
                    </div>
                    <Badge variant={badge.tagColor} size="sm" className="font-mono text-[9px]">
                      {badge.tag}
                    </Badge>
                  </div>

                  {/* Metrics snapshot if available */}
                  {node.metrics && (
                    <div className="mt-2 pt-2 border-t border-dark-border/40 grid grid-cols-2 gap-1.5 text-[10px] font-mono">
                      {Object.entries(node.metrics).map(([k, v]) => (
                        <div key={k} className="flex justify-between text-slate-muted">
                          <span>{k}:</span>
                          <span className="text-slate-text font-semibold">{v}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Arrow to Next Node if edge exists */}
                {edgeFromThis && idx < nodes.length - 1 && (
                  <div className="flex flex-col items-center justify-center py-0.5 text-slate-muted animate-pulse">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-dark-surface border border-dark-border/80 text-accent-primary mb-1">
                      {edgeFromThis.label || "Calls"}
                    </span>
                    <ArrowDown className="h-4 w-4 text-sky-400" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    );
  }

  // Fallback: If no edges returned by backend, show the verified affected services list
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between text-xs text-slate-muted">
        <div className="flex items-center gap-1.5">
          <Network className="h-3.5 w-3.5 text-accent-primary" />
          <span className="font-semibold text-slate-text">Affected Services</span>
        </div>
        <span className="text-[10px] font-mono">
          {affectedServices.length} reported services
        </span>
      </div>

      {affectedServices.length === 0 ? (
        <div className="p-4 text-center text-xs text-slate-muted border border-dashed border-dark-border rounded-lg">
          No affected microservice dependencies reported.
        </div>
      ) : (
        <div className="space-y-2">
          {affectedServices.map((svc) => (
            <div
              key={svc.service_id}
              className="p-3 rounded-lg border border-dark-border bg-dark-surface flex items-start gap-3"
            >
              <div className="p-1.5 rounded bg-dark-surfaceSecondary border border-dark-border text-accent-primary mt-0.5">
                <Server className="h-3.5 w-3.5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-slate-text">
                    {svc.service_id}
                  </span>
                  {svc.type && (
                    <Badge variant="outline" size="sm" className="text-[9px] font-mono uppercase">
                      {svc.type}
                    </Badge>
                  )}
                </div>
                <p className="text-xs text-slate-muted mt-1 leading-relaxed">
                  {svc.impact}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

