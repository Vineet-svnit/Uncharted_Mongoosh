"use client";

import React from "react";
import {
  ShieldAlert,
  ArrowRight,
  Sparkles,
  GitCommit,
  Network,
  Activity,
  CheckCircle2,
} from "lucide-react";

interface WelcomeScreenProps {
  onSelectPrompt: (promptText: string) => void;
}

const EXAMPLE_PROMPTS = [
  {
    title: "Checkout API Outage",
    prompt: "Why did Checkout API fail on October 28 between 14:00 and 14:25 UTC, and do we owe Acme Corp an SLA penalty?",
    tag: "High Severity",
    icon: Activity,
  },
  {
    title: "Database Slowdown vs DDoS",
    prompt: "Was the database slowdown caused by an external DDoS attack or an internal deployment regression?",
    tag: "Contradiction Check",
    icon: Network,
  },
  {
    title: "Historical Redis Failures",
    prompt: "Have we experienced similar Redis connection pool exhaustion incidents before in Auth Service?",
    tag: "Historical Correlate",
    icon: GitCommit,
  },
  {
    title: "Deployment Impact Verification",
    prompt: "Why did the deployment to auth-service fail yesterday and what microservices were affected?",
    tag: "Deployment Diff",
    icon: Sparkles,
  },
];

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({
  onSelectPrompt,
}) => {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 max-w-3xl mx-auto text-center animate-in fade-in duration-300">
      {/* Icon Badge */}
      <div className="relative mb-5">
        <div className="h-16 w-16 rounded-2xl bg-sky-500/10 border border-sky-500/30 flex items-center justify-center text-accent-primary shadow-lg shadow-sky-500/10">
          <ShieldAlert className="h-8 w-8" />
        </div>
        <div className="absolute -top-1 -right-1 h-4 w-4 rounded-full bg-accent-primary animate-ping opacity-60" />
      </div>

      {/* Main Heading */}
      <h1 className="text-3xl font-extrabold tracking-tight text-slate-text">
        Aegis<span className="text-accent-primary">RCA</span>
      </h1>
      <p className="mt-1 text-sm font-semibold uppercase tracking-widest text-accent-primary/80">
        Autonomous Incident Investigation
      </p>

      {/* Subtitle / Capabilities */}
      <div className="mt-4 flex flex-wrap items-center justify-center gap-x-4 gap-y-1.5 text-xs text-slate-muted max-w-lg">
        <span className="flex items-center gap-1">
          <CheckCircle2 className="h-3.5 w-3.5 text-accent-primary" /> Investigate incidents
        </span>
        <span className="text-slate-600">•</span>
        <span className="flex items-center gap-1">
          <CheckCircle2 className="h-3.5 w-3.5 text-accent-primary" /> Trace dependencies
        </span>
        <span className="text-slate-600">•</span>
        <span className="flex items-center gap-1">
          <CheckCircle2 className="h-3.5 w-3.5 text-accent-primary" /> Discover root causes
        </span>
        <span className="text-slate-600">•</span>
        <span className="flex items-center gap-1">
          <CheckCircle2 className="h-3.5 w-3.5 text-accent-primary" /> Verify evidence
        </span>
      </div>

      <p className="mt-6 text-sm text-slate-muted font-medium">
        What would you like to investigate?
      </p>

      {/* Example Prompts Grid */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-3 w-full text-left">
        {EXAMPLE_PROMPTS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(item.prompt)}
              className="group relative flex flex-col justify-between p-4 rounded-xl bg-dark-surface border border-dark-border hover:border-sky-500/50 hover:bg-dark-surfaceSecondary/80 transition-all duration-200 text-left shadow-sm hover:shadow-sky-500/5"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="p-1.5 rounded-md bg-dark-surfaceSecondary text-accent-primary border border-dark-border group-hover:border-sky-500/30">
                      <Icon className="h-3.5 w-3.5" />
                    </div>
                    <span className="text-xs font-semibold text-slate-text">
                      {item.title}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dark-surfaceSecondary border border-dark-border text-slate-muted">
                    {item.tag}
                  </span>
                </div>
                <p className="text-xs text-slate-muted line-clamp-2 leading-relaxed">
                  {item.prompt}
                </p>
              </div>

              <div className="mt-3 flex items-center text-[11px] font-medium text-accent-primary opacity-0 group-hover:opacity-100 transition-opacity">
                <span>Investigate incident</span>
                <ArrowRight className="h-3 w-3 ml-1 transform group-hover:translate-x-0.5 transition-transform" />
              </div>
            </button>
          );
        })}
      </div>

      {/* Evidence-backed note */}
      <div className="mt-8 pt-4 border-t border-dark-border/60 text-[11px] text-slate-muted/80 flex items-center gap-2">
        <Sparkles className="h-3.5 w-3.5 text-accent-primary" />
        <span>
          Powered by LangGraph Agentic Multi-Tool Reasoner &amp; Verified Telemetry Evidence
        </span>
      </div>
    </div>
  );
};

