"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, StopCircle, CornerDownLeft } from "lucide-react";
import { Button } from "@/components/ui/Button";

interface MessageInputProps {
  onSendMessage: (text: string) => void;
  isLoading: boolean;
  onCancel?: () => void;
  disabled?: boolean;
  placeholder?: string;
}

export const MessageInput: React.FC<MessageInputProps> = ({
  onSendMessage,
  isLoading,
  onCancel,
  disabled = false,
  placeholder = "Ask an incident question, e.g. Why did Checkout API fail between 14:00 and 14:25 UTC?...",
}) => {
  const [text, setText] = useState<string>("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea height
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        180
      )}px`;
    }
  }, [text]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleSend = () => {
    if (!text.trim() || isLoading || disabled) return;
    onSendMessage(text.trim());
    setText("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  return (
    <div className="p-4 border-t border-dark-border bg-dark-surface/90 backdrop-blur-md">
      <div className="max-w-4xl mx-auto relative rounded-xl border border-dark-border bg-dark-bg focus-within:border-sky-500/60 transition-all shadow-lg shadow-black/20">
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          rows={1}
          className="w-full resize-none bg-transparent px-4 py-3 text-sm text-slate-text placeholder-slate-500 focus:outline-none disabled:opacity-60 disabled:cursor-not-allowed max-h-48 min-h-[48px]"
        />

        <div className="flex items-center justify-between px-3 pb-2.5 pt-1">
          <div className="flex items-center gap-1.5 text-[11px] text-slate-muted/60">
            <span className="hidden sm:inline">Press</span>
            <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-mono text-[10px] bg-dark-surfaceSecondary border border-dark-border">
              <span>Enter</span>
              <CornerDownLeft className="h-2.5 w-2.5" />
            </kbd>
            <span className="hidden sm:inline">to send,</span>
            <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 font-mono text-[10px] bg-dark-surfaceSecondary border border-dark-border">
              Shift + Enter
            </kbd>
            <span className="hidden sm:inline">for newline</span>
          </div>

          <div className="flex items-center gap-2">
            {isLoading && onCancel ? (
              <Button
                variant="danger"
                size="sm"
                onClick={onCancel}
                className="h-8 px-3 text-xs gap-1.5"
                title="Cancel investigation stream"
              >
                <StopCircle className="h-3.5 w-3.5" />
                <span>Stop</span>
              </Button>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={handleSend}
                disabled={!text.trim() || disabled || isLoading}
                className="h-8 px-4 text-xs font-semibold shadow-md shadow-sky-500/10"
              >
                <span>Send</span>
                <Send className="h-3.5 w-3.5 ml-1" />
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

