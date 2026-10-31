"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Plus,
  MessageSquare,
  Trash2,
  Database,
  Cpu,
  Layers,
  ChevronRight,
  AlertCircle,
  HelpCircle,
} from "lucide-react";
import { Thread } from "@/types/chat";
import { HealthResponse } from "@/types/api";
import { formatRelativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { Skeleton } from "@/components/ui/Loading";

interface SidebarProps {
  threads: Thread[];
  activeThreadId?: string | null;
  loading: boolean;
  error: string | null;
  health: HealthResponse | null;
  healthError: string | null;
  onDeleteThread: (threadId: string) => Promise<void>;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  threads,
  activeThreadId,
  loading,
  error,
  health,
  healthError,
  onDeleteThread,
  onCloseMobile,
}) => {
  const router = useRouter();
  const [threadToDelete, setThreadToDelete] = useState<Thread | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const handleStartNewChat = () => {
    onCloseMobile?.();
    router.push("/chat");
  };

  const handleConfirmDelete = async () => {
    if (!threadToDelete) return;
    try {
      setIsDeleting(true);
      await onDeleteThread(threadToDelete.thread_id);
      if (activeThreadId === threadToDelete.thread_id) {
        router.push("/chat");
      }
      setThreadToDelete(null);
    } catch {
      // error handled in hook
    } finally {
      setIsDeleting(false);
    }
  };

  const isMongoConnected = health?.mongodb === "connected" || health?.mongodb === "mock-connected";
  const isAgentReady = health?.agent === "initialized" || health?.agent === "mock-initialized";

  return (
    <>
      <aside className="w-72 bg-dark-sidebar border-r border-dark-border flex flex-col h-full shrink-0 select-none">
        {/* Top: New Investigation Button */}
        <div className="p-3 border-b border-dark-border">
          <Button
            variant="primary"
            size="md"
            className="w-full justify-center gap-2 shadow-md shadow-sky-500/10 font-medium"
            onClick={handleStartNewChat}
          >
            <Plus className="h-4 w-4" />
            <span>New Investigation</span>
          </Button>
        </div>

        {/* Middle: Investigation History */}
        <div className="flex-1 overflow-y-auto px-2 py-3 space-y-1">
          <div className="px-3 pb-2 flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider text-slate-muted">
            <span>Recent Investigations</span>
            <span className="text-[10px] text-slate-muted/60">{threads.length}</span>
          </div>

          {loading && threads.length === 0 ? (
            <div className="space-y-2 p-2">
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </div>
          ) : error ? (
            <div className="p-3 text-xs text-rose-400 bg-rose-500/10 rounded-lg border border-rose-500/20 m-2 flex items-start gap-2">
              <AlertCircle className="h-4 w-4 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          ) : threads.length === 0 ? (
            <div className="py-8 px-4 text-center">
              <MessageSquare className="h-8 w-8 text-slate-muted/40 mx-auto mb-2" />
              <p className="text-xs text-slate-muted">No investigations yet</p>
              <p className="text-[11px] text-slate-muted/60 mt-1">
                Start an investigation above to begin analyzing incidents.
              </p>
            </div>
          ) : (
            <div className="space-y-1">
              {threads.map((t) => {
                const isActive = activeThreadId === t.thread_id;
                return (
                  <div
                    key={t.thread_id}
                    className={`group relative flex items-center justify-between rounded-lg px-3 py-2 text-xs transition-all ${
                      isActive
                        ? "bg-dark-surfaceSecondary border border-dark-border/80 text-slate-text font-medium shadow-xs"
                        : "text-slate-muted hover:bg-dark-surfaceSecondary/50 hover:text-slate-text"
                    }`}
                  >
                    <Link
                      href={`/chat/${t.thread_id}`}
                      onClick={onCloseMobile}
                      className="flex-1 min-w-0 pr-2 flex items-center gap-2.5"
                    >
                      <div
                        className={`h-2 w-2 rounded-full shrink-0 ${
                          isActive
                            ? "bg-accent-primary ring-2 ring-sky-400/20"
                            : "bg-slate-600 group-hover:bg-slate-500"
                        }`}
                      />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs leading-snug">
                          {t.title || "Untitled Investigation"}
                        </p>
                        <p className="text-[10px] text-slate-muted/70 mt-0.5">
                          {formatRelativeTime(t.updated_at || t.created_at)}
                        </p>
                      </div>
                    </Link>

                    {/* Delete action button */}
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setThreadToDelete(t);
                      }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded text-slate-muted hover:text-rose-400 hover:bg-dark-surface transition-opacity"
                      title="Delete investigation"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Bottom: Service Health and Connection Status */}
        <div className="p-3 border-t border-dark-border bg-dark-surface/50 text-[11px] space-y-2">
          <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-muted px-1">
            System Connectivity
          </div>

          <div className="space-y-1.5 px-1">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-slate-muted">
                <Database className="h-3.5 w-3.5" />
                <span>MongoDB State</span>
              </div>
              <span
                className={`font-mono text-[10px] font-medium ${
                  isMongoConnected ? "text-emerald-400" : "text-rose-400"
                }`}
              >
                {health?.mongodb || (healthError ? "DISCONNECTED" : "CONNECTING")}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-slate-muted">
                <Cpu className="h-3.5 w-3.5" />
                <span>LangGraph Agent</span>
              </div>
              <span
                className={`font-mono text-[10px] font-medium ${
                  isAgentReady ? "text-emerald-400" : "text-amber-400"
                }`}
              >
                {health?.agent || "INITIALIZING"}
              </span>
            </div>

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1.5 text-slate-muted">
                <Layers className="h-3.5 w-3.5" />
                <span>Data Layer</span>
              </div>
              <span className="font-mono text-[10px] font-medium text-slate-muted">
                {health?.data_layer || "STANDBY"}
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-dark-border/60 flex items-center justify-between text-slate-muted/60 text-[10px] px-1">
            <span>AegisRCA v1.0.0</span>
            <span>FastAPI :8000</span>
          </div>
        </div>
      </aside>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!threadToDelete}
        onClose={() => setThreadToDelete(null)}
        title="Delete Investigation"
        description="Are you sure you want to delete this investigation thread?"
      >
        <div className="space-y-4">
          <p className="text-xs text-slate-muted">
            This will permanently remove the conversation titled{" "}
            <span className="text-slate-text font-semibold">
              "{threadToDelete?.title}"
            </span>
            , along with all associated runs, tool logs, checkpoints, and reports.
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setThreadToDelete(null)}
              disabled={isDeleting}
            >
              Cancel
            </Button>
            <Button
              variant="danger"
              size="sm"
              onClick={handleConfirmDelete}
              isLoading={isDeleting}
            >
              Delete Permanently
            </Button>
          </div>
        </div>
      </Modal>
    </>
  );
};

