import React from "react";
import { ShieldAlert } from "lucide-react";

interface TypingIndicatorProps {
  message?: string;
  stage?: string;
}

export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
  message = "Agent investigating...",
  stage = "planning",
}) => {
  return (
    <div className="flex items-start gap-3 my-3 animate-in fade-in duration-200">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/10 border border-sky-500/30 text-accent-primary shrink-0 radar-active">
        <ShieldAlert className="h-4 w-4" />
      </div>
      <div className="rounded-xl border border-dark-border bg-dark-surface px-4 py-2.5 text-xs text-slate-text flex items-center gap-3 shadow-md">
        <div className="flex space-x-1">
          <div className="h-1.5 w-1.5 rounded-full bg-accent-primary animate-bounce [animation-delay:-0.3s]" />
          <div className="h-1.5 w-1.5 rounded-full bg-accent-primary animate-bounce [animation-delay:-0.15s]" />
          <div className="h-1.5 w-1.5 rounded-full bg-accent-primary animate-bounce" />
        </div>
        <span className="font-mono text-slate-muted">{message}</span>
        {stage && (
          <span className="text-[10px] uppercase font-mono tracking-wider px-1.5 py-0.5 rounded bg-dark-surfaceSecondary text-accent-primary border border-dark-border">
            {stage}
          </span>
        )}
      </div>
    </div>
  );
};

