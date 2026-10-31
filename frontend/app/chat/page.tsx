"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { InvestigationReport } from "@/components/investigation/InvestigationReport";
import { createThread } from "@/lib/api";
import { InvestigationResult, EvidenceItem } from "@/types/investigation";

export default function NewChatPage() {
  const router = useRouter();
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const handleSendMessage = async (text: string) => {
    try {
      setIsCreating(true);
      setCreateError(null);
      // Derive a short informative title from the prompt
      const title = text.length > 50 ? `${text.slice(0, 47)}...` : text;
      const thread = await createThread(title);
      // Store initial query in sessionStorage so [threadId]/page.tsx picks it up immediately
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`pending_prompt_${thread.thread_id}`, text);
      }
      router.push(`/chat/${thread.thread_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to initiate thread";
      setCreateError(msg);
      setIsCreating(false);
    }
  };

  return (
    <AppLayout
      activeThreadId={null}
      isInspectorOpen={isInspectorOpen}
      onToggleInspector={() => setIsInspectorOpen((prev) => !prev)}
    >
      <ChatWindow
        messages={[]}
        loadingMessages={false}
        chatError={createError}
        isStreaming={isCreating}
        currentStage="planning"
        stageMessage={isCreating ? "Initializing new incident investigation thread..." : ""}
        toolExecutions={[]}
        streamError={null}
        onSendMessage={handleSendMessage}
        onCancelStream={() => setIsCreating(false)}
        onCitationClick={() => {}}
        onOpenInspector={() => setIsInspectorOpen(true)}
      />
    </AppLayout>
  );
}

