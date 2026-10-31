"use client";

import { useState, useEffect, useCallback } from "react";
import { Thread } from "@/types/chat";
import { getThreads, createThread as apiCreateThread, deleteThread as apiDeleteThread, getHealth } from "@/lib/api";
import { HealthResponse } from "@/types/api";

export function useThreads(activeThreadId?: string) {
  const [threads, setThreads] = useState<Thread[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  const fetchThreads = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getThreads();
      setThreads(res.threads || []);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load threads";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  const checkHealth = useCallback(async () => {
    try {
      setHealthError(null);
      const h = await getHealth();
      setHealth(h);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Backend unavailable";
      setHealthError(msg);
      setHealth(null);
    }
  }, []);

  useEffect(() => {
    fetchThreads();
    checkHealth();
  }, [fetchThreads, checkHealth]);

  const createNewThread = async (title?: string): Promise<Thread> => {
    try {
      const newThread = await apiCreateThread(title);
      setThreads((prev) => [newThread, ...prev.filter((t) => t.thread_id !== newThread.thread_id)]);
      return newThread;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create thread";
      setError(msg);
      throw err;
    }
  };

  const deleteExistingThread = async (threadId: string): Promise<void> => {
    try {
      await apiDeleteThread(threadId);
      setThreads((prev) => prev.filter((t) => t.thread_id !== threadId));
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to delete thread";
      setError(msg);
      throw err;
    }
  };

  const updateThreadActivity = (threadId: string, runId?: string) => {
    setThreads((prev) =>
      prev.map((t) => {
        if (t.thread_id === threadId) {
          return {
            ...t,
            updated_at: new Date().toISOString(),
            message_count: t.message_count + 1,
            last_run_id: runId || t.last_run_id,
          };
        }
        return t;
      })
    );
  };

  return {
    threads,
    loading,
    error,
    health,
    healthError,
    refreshThreads: fetchThreads,
    refreshHealth: checkHealth,
    createThread: createNewThread,
    deleteThread: deleteExistingThread,
    updateThreadActivity,
  };
}

