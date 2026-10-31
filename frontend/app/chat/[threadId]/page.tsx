"use client";

import React, { useEffect, useRef } from "react";
import { useParams } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { InvestigationReport } from "@/components/investigation/InvestigationReport";
import { useChat } from "@/hooks/useChat";

export default function ChatThreadPage() {
  const params = useParams();
  const threadId = (params?.threadId as string) || "";

  const {
    messages,
    loadingMessages,
    chatError,
    stream,
    selectedResult,
    inspectedEvidence,
    setInspectedEvidence,
    isInspectorOpen,
    setIsInspectorOpen,
    sendMessage,
    handleCitationClick,
    refreshMessages,
  } = useChat(threadId);

  const initialSentRef = useRef<boolean>(false);

  // Check for pending prompt from welcome page creation
  useEffect(() => {
    if (typeof window !== "undefined" && threadId && !initialSentRef.current) {
      const pendingKey = `pending_prompt_${threadId}`;
      const pending = sessionStorage.getItem(pendingKey);
      if (pending) {
        sessionStorage.removeItem(pendingKey);
        initialSentRef.current = true;
        sendMessage(pending);
      }
    }
  }, [threadId, sendMessage]);

  const inspectorContent = selectedResult ? (
    <InvestigationReport
      result={selectedResult}
      inspectedEvidence={inspectedEvidence}
      onCloseInspectedEvidence={() => setInspectedEvidence(null)}
      onSelectEvidence={(ev) => setInspectedEvidence(ev)}
    />
  ) : null;

  return (
    <AppLayout
      activeThreadId={threadId}
      activeIncidentId={selectedResult?.incident_id}
      isInspectorOpen={isInspectorOpen && !!selectedResult}
      onToggleInspector={() => setIsInspectorOpen((prev) => !prev)}
      inspectorContent={inspectorContent}
    >
      <ChatWindow
        messages={messages}
        loadingMessages={loadingMessages}
        chatError={chatError}
        isStreaming={stream.isStreaming}
        currentStage={stream.currentStage}
        stageMessage={stream.stageMessage}
        toolExecutions={stream.toolExecutions}
        streamError={stream.streamError}
        onSendMessage={sendMessage}
        onCancelStream={stream.cancelInvestigation}
        onCitationClick={handleCitationClick}
        onOpenInspector={() => setIsInspectorOpen(true)}
        onRetry={refreshMessages}
      />
    </AppLayout>
  );
}

