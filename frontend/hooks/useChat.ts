"use client";

import { useState, useEffect, useCallback } from "react";
import { ChatMessage } from "@/types/chat";
import { InvestigationResult, EvidenceItem } from "@/types/investigation";
import { AssistantResultPayload } from "@/types/api";
import { getThreadMessages } from "@/lib/api";
import { useInvestigationStream } from "./useInvestigationStream";

export type InspectorTab =
  | "overview"
  | "timeline"
  | "topology"
  | "evidence"
  | "sla"
  | "telemetry";

export function useChat(
  threadId: string | null,
  onActivityUpdate?: (threadId: string, runId?: string) => void
) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false);
  const [chatError, setChatError] = useState<string | null>(null);

  // Inspector & modal states
  const [selectedResult, setSelectedResult] = useState<InvestigationResult | null>(null);
  const [inspectedEvidence, setInspectedEvidence] = useState<EvidenceItem | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(true);
  const [activeInspectorTab, setActiveInspectorTab] = useState<InspectorTab>("overview");

  const stream = useInvestigationStream();

  // Load chronological messages whenever threadId changes
  const loadMessages = useCallback(async (id: string) => {
    try {
      setLoadingMessages(true);
      setChatError(null);
      const res = await getThreadMessages(id);
      const loadedMsgs = res.messages || [];
      setMessages(loadedMsgs);

      // Find the latest message with an investigation result
      for (let i = loadedMsgs.length - 1; i >= 0; i--) {
        const inv = loadedMsgs[i].metadata?.investigation_result;
        if (inv) {
          setSelectedResult(inv);
          break;
        }
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load messages";
      setChatError(msg);
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  useEffect(() => {
    if (threadId) {
      loadMessages(threadId);
      stream.resetStream();
    } else {
      setMessages([]);
      setSelectedResult(null);
      stream.resetStream();
    }
  }, [threadId, loadMessages]);

  // Send inquiry message
  const sendMessage = async (text: string) => {
    if (!threadId || !text.trim() || stream.isStreaming) return;

    const userMsgId = `temp-user-${Date.now()}`;
    const optimisticUserMsg: ChatMessage = {
      message_id: userMsgId,
      thread_id: threadId,
      role: "user",
      content: text.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, optimisticUserMsg]);
    setChatError(null);

    await stream.startInvestigation(
      threadId,
      text.trim(),
      (asstPayload: AssistantResultPayload) => {
        const asstMsg: ChatMessage = {
          message_id: asstPayload.message_id,
          thread_id: threadId,
          role: "assistant",
          content: asstPayload.content,
          created_at: new Date().toISOString(),
          metadata: {
            investigation_result: asstPayload.investigation_result,
            citations: asstPayload.investigation_result?.supporting_evidence,
          },
        };

        setMessages((prev) => [...prev, asstMsg]);
        if (asstPayload.investigation_result) {
          setSelectedResult(asstPayload.investigation_result);
          setIsInspectorOpen(true);
        }
      },
      () => {
        // On complete
        onActivityUpdate?.(threadId, stream.runId || undefined);
      }
    );
  };

  // Click citation handler: opens evidence detail
  const handleCitationClick = useCallback(
    (evidenceId: string) => {
      if (!selectedResult) return;

      // Look in supporting, contradicting, and citations lists
      const allEvidence: EvidenceItem[] = [
        ...(selectedResult.supporting_evidence || []),
        ...(selectedResult.contradicting_evidence || []),
        ...((selectedResult.citations as EvidenceItem[]) || []),
      ];

      const found = allEvidence.find(
        (e) =>
          e.evidence_id?.toLowerCase() === evidenceId.toLowerCase() ||
          e.source_id?.toLowerCase() === evidenceId.toLowerCase()
      );

      if (found) {
        setInspectedEvidence(found);
      } else {
        // Construct a fallback preview
        setInspectedEvidence({
          evidence_id: evidenceId,
          source_type: "citation",
          source_id: evidenceId,
          title: `Evidence ${evidenceId}`,
          content: `Referenced citation ${evidenceId} in investigation findings.`,
          classification: "supporting",
        });
      }
    },
    [selectedResult]
  );

  return {
    messages,
    loadingMessages,
    chatError,
    stream,
    selectedResult,
    setSelectedResult,
    inspectedEvidence,
    setInspectedEvidence,
    isInspectorOpen,
    setIsInspectorOpen,
    activeInspectorTab,
    setActiveInspectorTab,
    sendMessage,
    handleCitationClick,
    refreshMessages: () => threadId && loadMessages(threadId),
  };
}

