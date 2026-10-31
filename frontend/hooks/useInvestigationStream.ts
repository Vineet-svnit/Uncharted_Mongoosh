"use client";

import { useState, useRef, useCallback } from "react";
import { ToolExecution, InvestigationStage } from "@/types/chat";
import {
  RunStartedPayload,
  StatusPayload,
  ToolStartedPayload,
  ToolCompletedPayload,
  AssistantResultPayload,
  DonePayload,
  ErrorPayload,
} from "@/types/api";
import { streamMessage } from "@/lib/api";
import { getToolInfo } from "@/lib/utils";

export interface UseInvestigationStreamReturn {
  isStreaming: boolean;
  currentStage: InvestigationStage;
  stageMessage: string;
  runId: string | null;
  toolExecutions: ToolExecution[];
  streamError: string | null;
  startInvestigation: (
    threadId: string,
    message: string,
    onAssistantResult?: (res: AssistantResultPayload) => void,
    onComplete?: () => void
  ) => Promise<void>;
  cancelInvestigation: () => void;
  resetStream: () => void;
}

export function useInvestigationStream(): UseInvestigationStreamReturn {
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [currentStage, setCurrentStage] = useState<InvestigationStage>("idle");
  const [stageMessage, setStageMessage] = useState<string>("");
  const [runId, setRunId] = useState<string | null>(null);
  const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);
  const [streamError, setStreamError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  const resetStream = useCallback(() => {
    setIsStreaming(false);
    setCurrentStage("idle");
    setStageMessage("");
    setRunId(null);
    setToolExecutions([]);
    setStreamError(null);
    abortControllerRef.current = null;
  }, []);

  const cancelInvestigation = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    setCurrentStage("failed");
    setStageMessage("Investigation cancelled by user");
  }, []);

  const startInvestigation = useCallback(
    async (
      threadId: string,
      message: string,
      onAssistantResult?: (res: AssistantResultPayload) => void,
      onComplete?: () => void
    ) => {
      // Abort any existing stream
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setIsStreaming(true);
      setCurrentStage("planning");
      setStageMessage("Initiating incident investigation...");
      setToolExecutions([]);
      setStreamError(null);

      const handlers = {
        onRunStarted: (data: RunStartedPayload) => {
          setRunId(data.run_id);
          setCurrentStage("planning");
          setStageMessage("Agent initialized. Planning investigation...");
        },
        onStatus: (data: StatusPayload) => {
          const stageLower = (data.stage || "").toLowerCase();
          if (stageLower.includes("plan")) {
            setCurrentStage("planning");
          } else if (stageLower.includes("verif")) {
            setCurrentStage("verification");
          } else if (stageLower.includes("report")) {
            setCurrentStage("report_generation");
          } else {
            setCurrentStage("investigating");
          }
          setStageMessage(data.message || data.stage);
        },
        onToolStarted: (data: ToolStartedPayload) => {
          setCurrentStage("investigating");
          const toolMeta = getToolInfo(data.tool);
          const toolId = `${data.tool}-${Date.now()}`;
          const newToolExec: ToolExecution = {
            id: toolId,
            tool: data.tool,
            label: toolMeta.label,
            status: "running",
            started_at: new Date().toISOString(),
            message: data.message,
          };

          setToolExecutions((prev) => {
            // Check if tool is already running
            const existingIdx = prev.findIndex(
              (t) => t.tool === data.tool && t.status === "running"
            );
            if (existingIdx !== -1) {
              const updated = [...prev];
              updated[existingIdx] = {
                ...updated[existingIdx],
                message: data.message,
              };
              return updated;
            }
            return [...prev, newToolExec];
          });
          setStageMessage(toolMeta.label);
        },
        onToolCompleted: (data: ToolCompletedPayload) => {
          const toolMeta = getToolInfo(data.tool);
          setToolExecutions((prev) => {
            // Find matching running tool, or fallback to the last tool or composite
            let matched = false;
            const updated = prev.map((t) => {
              if (
                !matched &&
                (t.tool === data.tool || data.tool === "investigation_tools") &&
                t.status === "running"
              ) {
                matched = true;
                return {
                  ...t,
                  status: "completed" as const,
                  completed_at: new Date().toISOString(),
                  evidence_count: data.evidence_count,
                  summary: data.summary,
                };
              }
              return t;
            });

            if (!matched) {
              // Add as completed directly
              updated.push({
                id: `${data.tool}-${Date.now()}`,
                tool: data.tool,
                label: toolMeta.label,
                status: "completed" as const,
                completed_at: new Date().toISOString(),
                evidence_count: data.evidence_count,
                summary: data.summary,
              });
            }
            return updated;
          });
        },
        onAssistantResult: (data: AssistantResultPayload) => {
          setCurrentStage("report_generation");
          setStageMessage("Root cause analysis synthesized.");
          onAssistantResult?.(data);
        },
        onDone: (data: DonePayload) => {
          setCurrentStage("completed");
          setStageMessage("Investigation complete");
          setIsStreaming(false);
          onComplete?.();
        },
        onError: (data: ErrorPayload) => {
          setCurrentStage("failed");
          const msg = data.message || "Investigation failed";
          setStreamError(msg);
          setStageMessage(`Error: ${msg}`);
          setIsStreaming(false);
        },
      };

      try {
        await streamMessage(threadId, message, handlers, controller.signal);
      } catch (err: unknown) {
        if (!controller.signal.aborted) {
          const msg = err instanceof Error ? err.message : "Investigation failed unexpectedly";
          setStreamError(msg);
          setCurrentStage("failed");
          setStageMessage(msg);
          setIsStreaming(false);
        }
      }
    },
    []
  );

  return {
    isStreaming,
    currentStage,
    stageMessage,
    runId,
    toolExecutions,
    streamError,
    startInvestigation,
    cancelInvestigation,
    resetStream,
  };
}

