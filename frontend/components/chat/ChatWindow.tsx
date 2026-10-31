"use client";

import React, { useRef, useEffect } from "react";
import { ChatMessage as ChatMessageType, ToolExecution, InvestigationStage } from "@/types/chat";
import { ChatMessage } from "./ChatMessage";
import { WelcomeScreen } from "./WelcomeScreen";
import { MessageInput } from "./MessageInput";
import { InvestigationActivity } from "@/components/investigation/InvestigationActivity";
import { TypingIndicator } from "./TypingIndicator";
import { Skeleton } from "@/components/ui/Loading";
import { AlertCircle } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface ChatWindowProps {
  messages: ChatMessageType[];
  loadingMessages: boolean;
  chatError: string | null;
  isStreaming: boolean;
  currentStage: InvestigationStage;
  stageMessage: string;
  toolExecutions: ToolExecution[];
  streamError: string | null;
  onSendMessage: (message: string) => void;
  onCancelStream: () => void;
  onCitationClick: (evidenceId: string) => void;
  onOpenInspector: () => void;
  onRetry?: () => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({
  messages,
  loadingMessages,
  chatError,
  isStreaming,
  currentStage,
  stageMessage,
  toolExecutions,
  streamError,
  onSendMessage,
  onCancelStream,
  onCitationClick,
  onOpenInspector,
  onRetry,
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages or streaming activity
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, toolExecutions, isStreaming]);

  const isEmpty = messages.length === 0 && !isStreaming;

  return (
    <div className="flex flex-col h-full w-full bg-dark-bg relative overflow-hidden">
      {/* Scrollable message flow */}
      <div className="flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="max-w-4xl mx-auto min-h-full flex flex-col justify-between">
          {loadingMessages ? (
            <div className="space-y-4 my-8">
              <Skeleton className="h-20 w-3/4 rounded-xl" />
              <Skeleton className="h-32 w-full rounded-xl ml-auto" />
              <Skeleton className="h-24 w-2/3 rounded-xl" />
            </div>
          ) : isEmpty ? (
            <WelcomeScreen onSelectPrompt={onSendMessage} />
          ) : (
            <div className="space-y-4 pb-4">
              {/* Message List */}
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.message_id}
                  message={msg}
                  onCitationClick={onCitationClick}
                  onOpenInspector={onOpenInspector}
                />
              ))}

              {/* Real-time Live Investigation Activity during SSE stream */}
              {(isStreaming || toolExecutions.length > 0 || streamError) && (
                <div className="my-2">
                  <InvestigationActivity
                    stage={currentStage}
                    stageMessage={stageMessage}
                    toolExecutions={toolExecutions}
                    isStreaming={isStreaming}
                    error={streamError}
                  />
                </div>
              )}

              {/* Streaming typing indicator if early in planning with no tools yet */}
              {isStreaming && toolExecutions.length === 0 && (
                <TypingIndicator
                  message={stageMessage || "Agent analyzing query..."}
                  stage={currentStage}
                />
              )}

              {/* General chat error if any */}
              {chatError && (
                <div className="p-4 my-4 rounded-xl border border-rose-500/30 bg-rose-950/20 text-rose-300 text-xs flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
                    <span>{chatError}</span>
                  </div>
                  {onRetry && (
                    <Button variant="outline" size="sm" onClick={onRetry}>
                      Retry
                    </Button>
                  )}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Pinned Bottom Message Input */}
      <MessageInput
        onSendMessage={onSendMessage}
        isLoading={isStreaming}
        onCancel={onCancelStream}
        disabled={loadingMessages}
      />
    </div>
  );
};

