"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { AppLayout } from "@/components/layout/AppLayout";
import { ChatWindow } from "@/components/chat/ChatWindow";
import { createThread } from "@/lib/api";

export default function ChatPage() {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);

  const handleSendMessage = async (text: string) => {
    if (!text.trim() || isCreating) return;

    try {
      setIsCreating(true);
      setCreateError(null);

      // Create new thread backed by MongoDB run repository
      const thread = await createThread(text.trim());

      // Store initial prompt in session storage to trigger automatic execution in thread view
      if (typeof window !== "undefined") {
        sessionStorage.setItem(`pending_prompt_${thread.thread_id}`, text.trim());
      }

      router.push(`/chat/${thread.thread_id}`);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to create investigation session";
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
        onOpenInspectorForResult={() => setIsInspectorOpen(true)}
      />
    </AppLayout>
  );
}
