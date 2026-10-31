"use client";

import React from "react";
import {
  ShieldAlert,
  PanelRightClose,
  PanelRightOpen,
  Menu,
  Activity,
  Server,
  Zap,
} from "lucide-react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IS_MOCK_MODE } from "@/lib/api";
import { HealthResponse } from "@/types/api";

interface HeaderProps {
  onToggleSidebar?: () => void;
  isInspectorOpen: boolean;
  onToggleInspector: () => void;
  health: HealthResponse | null;
  healthError: string | null;
  activeIncidentId?: string | null;
}

export const Header: React.FC<HeaderProps> = ({
  onToggleSidebar,
  isInspectorOpen,
  onToggleInspector,
  health,
  healthError,
  activeIncidentId,
}) => {
  const isHealthy = health?.status === "ok" && !healthError;

  return (
    <header className="h-14 border-b border-dark-border bg-dark-surface/90 backdrop-blur-md px-4 flex items-center justify-between z-20 shrink-0">
      {/* Left items */}
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="md:hidden p-1.5 rounded-lg text-slate-muted hover:text-slate-text hover:bg-dark-surfaceSecondary"
            aria-label="Toggle sidebar"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/10 border border-sky-500/30 text-accent-primary">
            <ShieldAlert className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold tracking-tight text-slate-text">
                Aegis<span className="text-accent-primary">RCA</span>
              </span>
              <span className="hidden sm:inline-block text-[11px] font-mono text-slate-muted/70 px-1.5 py-0.5 rounded bg-dark-surfaceSecondary border border-dark-border">
                SRE INCIDENT OPS
              </span>
            </div>
          </div>
        </div>

        {activeIncidentId && (
          <div className="hidden lg:flex items-center ml-4 pl-4 border-l border-dark-border">
            <span className="text-xs text-slate-muted mr-2">Incident:</span>
            <Badge variant="warning" size="sm" className="font-mono">
              {activeIncidentId}
            </Badge>
          </div>
        )}
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2.5">
        {/* Mock Mode / Demo data indicator */}
        {IS_MOCK_MODE && (
          <Badge
            variant="warning"
            size="sm"
            className="font-mono text-[11px] font-semibold tracking-wide bg-amber-500/20 border-amber-500/40 text-amber-300"
          >
            <Zap className="h-3 w-3 mr-1 text-amber-400" />
            DEMO DATA MODE
          </Badge>
        )}

        {/* Backend health indicator */}
        <div
          className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-dark-surfaceSecondary/60 border border-dark-border text-xs"
          title={
            isHealthy
              ? `Backend: Online | MongoDB: ${health?.mongodb} | Agent: ${health?.agent}`
              : `Backend Error: ${healthError || "Offline"}`
          }
        >
          <div
            className={`h-2 w-2 rounded-full ${
              isHealthy
                ? "bg-emerald-400 animate-pulse"
                : "bg-rose-500"
            }`}
          />
          <span className="text-slate-muted text-[11px] font-mono">
            {isHealthy ? "AGENT ONLINE" : "BACKEND OFFLINE"}
          </span>
        </div>

        {/* Inspector toggle button */}
        <Button
          variant="outline"
          size="sm"
          onClick={onToggleInspector}
          className="text-xs gap-1.5 h-8 text-slate-muted hover:text-slate-text"
          title={isInspectorOpen ? "Hide investigation inspector" : "Show investigation inspector"}
        >
          {isInspectorOpen ? (
            <>
              <PanelRightClose className="h-4 w-4 text-accent-primary" />
              <span className="hidden md:inline">Close Inspector</span>
            </>
          ) : (
            <>
              <PanelRightOpen className="h-4 w-4 text-accent-primary" />
              <span className="hidden md:inline">Open Inspector</span>
            </>
          )}
        </Button>
      </div>
    </header>
  );
};

