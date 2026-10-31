"use client";

import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ShieldAlert,
  User,
  Copy,
  Check,
  FileSearch,
  ExternalLink,
  ChevronRight,
} from "lucide-react";
import { ChatMessage as ChatMessageType } from "@/types/chat";
import { InvestigationResult } from "@/types/investigation";
import { formatTime } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";

interface ChatMessageProps {
  message: ChatMessageType;
  onCitationClick?: (evidenceId: string) => void;
  /** Called with the specific investigation result for this message */
  onOpenInspector?: (result: InvestigationResult) => void;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({
  message,
  onCitationClick,
  onOpenInspector,
}) => {
  const isAssistant = message.role === "assistant";
  const [copied, setCopied] = useState<boolean>(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const invResult = message.metadata?.investigation_result as InvestigationResult | undefined;

  // Custom text renderer to intercept [EVD-XXX] citation badges and make them interactive
  const renderContentWithCitations = (text: string) => {
    const citationRegex = /\[(EVD-[A-Za-z0-9_-]+)\]/g;
    const parts: React.ReactNode[] = [];
    let lastIndex = 0;
    let match;

    while ((match = citationRegex.exec(text)) !== null) {
      if (match.index > lastIndex) {
        parts.push(text.substring(lastIndex, match.index));
      }
      const evidenceId = match[1];
      parts.push(
        <button
          key={`${evidenceId}-${match.index}`}
          onClick={() => onCitationClick?.(evidenceId)}
          className="inline-flex items-center gap-0.5 mx-1 px-1.5 py-0.2 rounded text-[11px] font-mono font-semibold bg-sky-500/15 text-accent-primary border border-sky-500/30 hover:bg-sky-500/25 hover:border-sky-400 transition-colors align-baseline"
          title={`Click to inspect evidence details for ${evidenceId}`}
        >
          <span>[{evidenceId}]</span>
          <ExternalLink className="h-2.5 w-2.5 ml-0.5 opacity-70" />
        </button>
      );
      lastIndex = match.index + match[0].length;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts;
  };

  return (
    <div
      className={`group flex items-start gap-3 my-4 ${
        isAssistant ? "justify-start" : "justify-end"
      }`}
    >
      {/* Assistant Avatar */}
      {isAssistant && (
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-sky-500/10 border border-sky-500/30 text-accent-primary shrink-0 mt-0.5 shadow-sm">
          <ShieldAlert className="h-4 w-4" />
        </div>
      )}

      {/* Message Bubble Container */}
      <div
        className={`max-w-[85%] md:max-w-[78%] rounded-2xl px-4 py-3 shadow-md ${
          isAssistant
            ? "bg-dark-surface border border-dark-border text-slate-text"
            : "bg-dark-surfaceSecondary border border-sky-500/30 text-slate-text"
        }`}
      >
        {/* Header line: Role and Timestamp */}
        <div className="flex items-center justify-between gap-4 pb-2 mb-2 border-b border-dark-border/40 text-[11px]">
          <div className="flex items-center gap-2">
            <span
              className={`font-mono font-semibold uppercase tracking-wider ${
                isAssistant ? "text-accent-primary" : "text-indigo-400"
              }`}
            >
              {isAssistant ? "AegisRCA Agent" : "You (SRE On-Call)"}
            </span>
            {invResult?.root_cause && (
              <Badge variant="success" size="sm" className="text-[10px]">
                Root Cause Identified
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2 text-slate-muted">
            <span className="font-mono">{formatTime(message.created_at)}</span>
            <button
              onClick={handleCopy}
              className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-dark-surfaceSecondary hover:text-slate-text transition-all"
              title="Copy message"
            >
              {copied ? (
                <Check className="h-3 w-3 text-emerald-400" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
            </button>
          </div>
        </div>

        {/* Message Body */}
        <div className="text-xs sm:text-sm leading-relaxed prose prose-invert max-w-none prose-p:my-2 prose-headings:text-slate-text prose-headings:my-2 prose-h3:text-sm prose-h3:font-semibold prose-pre:my-2 prose-ul:my-2 prose-li:my-0.5">
          {isAssistant ? (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => {
                  return (
                    <p className="my-2">
                      {React.Children.map(children, (child) => {
                        if (typeof child === "string") {
                          return renderContentWithCitations(child);
                        }
                        return child;
                      })}
                    </p>
                  );
                },
                li: ({ children }) => {
                  return (
                    <li className="my-0.5">
                      {React.Children.map(children, (child) => {
                        if (typeof child === "string") {
                          return renderContentWithCitations(child);
                        }
                        return child;
                      })}
                    </li>
                  );
                },
                code: ({ node, className, children, ...props }) => {
                  const match = /language-(\w+)/.exec(className || "");
                  const isInline = !match && !String(children).includes("\n");
                  if (isInline) {
                    return (
                      <code
                        className="bg-dark-surfaceSecondary px-1.5 py-0.5 rounded text-accent-primary font-mono text-[11px] border border-dark-border"
                        {...props}
                      >
                        {children}
                      </code>
                    );
                  }
                  return (
                    <pre className="relative overflow-x-auto my-2 rounded-lg bg-slate-950 p-3 font-mono text-xs border border-dark-border text-slate-200">
                      <code>{children}</code>
                    </pre>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          ) : (
            <div className="whitespace-pre-wrap">{message.content}</div>
          )}
        </div>

        {/* Investigation Inspector Action Callout — per-message result */}
        {isAssistant && invResult && onOpenInspector && (
          <div className="mt-3 pt-3 border-t border-dark-border/60 flex flex-wrap items-center justify-between gap-2 bg-dark-surfaceSecondary/40 -mx-4 -mb-3 p-3 rounded-b-2xl">
            <div className="flex items-center gap-2">
              <FileSearch className="h-4 w-4 text-accent-primary" />
              <span className="text-xs text-slate-muted">
                Full RCA Report, Timeline, and Evidence ready
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onOpenInspector(invResult)}
              className="text-xs py-1 h-7 text-accent-primary border-sky-500/30 hover:bg-sky-500/10"
            >
              <span>Examine Inspector</span>
              <ChevronRight className="h-3 w-3 ml-1" />
            </Button>
          </div>
        )}
      </div>

      {/* User Avatar */}
      {!isAssistant && (
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-indigo-500/20 border border-indigo-500/30 text-indigo-400 shrink-0 mt-0.5">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
};
