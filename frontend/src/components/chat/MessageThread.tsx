"use client";

/**
 * MessageThread — Scrollable container that renders all chat messages.
 *
 * Auto-scrolls to the bottom whenever a new message is added.
 */

import { useEffect, useRef } from "react";
import MessageBubble from "@/components/chat/MessageBubble";
import type { ChatMessage } from "@/hooks/useChat";

interface MessageThreadProps {
  messages: ChatMessage[];
  showCitations: boolean;
  isLoading: boolean;
  onDomainSwitch?: (domain: string) => void;
}

export default function MessageThread({
  messages,
  showCitations,
  isLoading,
  onDomainSwitch,
}: MessageThreadProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  if (messages.length === 0 && !isLoading) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 text-gray-400">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="40"
          height="40"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
          className="opacity-40"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
        <p className="text-sm">Ask a question about your policy documents</p>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col overflow-y-auto px-4 py-4">
      <div className="mx-auto w-full max-w-3xl space-y-4">
        {messages.map((msg) =>
          msg.availableDomains ? (
            <div key={msg.id} className="flex justify-start">
              <div className="max-w-lg rounded-2xl rounded-bl-sm border border-amber-200 bg-amber-50 px-4 py-3 shadow-sm">
                <div className="mb-2 flex items-center gap-2">
                  {/* Lock icon */}
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 text-amber-600" aria-hidden="true">
                    <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
                    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
                  </svg>
                  <p className="text-sm font-medium text-amber-900">Access Restricted</p>
                </div>
                <p className="mb-3 text-sm text-amber-800">{msg.content}</p>
                {msg.availableDomains.length > 0 && (
                  <div className="flex flex-wrap gap-2">
                    <p className="w-full text-xs font-medium text-amber-700">
                      Switch to a domain you have access to:
                    </p>
                    {msg.availableDomains.map((domain) => (
                      <button
                        key={domain}
                        type="button"
                        onClick={() => onDomainSwitch?.(domain)}
                        className="rounded-full border border-amber-300 bg-white px-3 py-1 text-xs font-medium text-amber-800 transition-colors hover:bg-amber-100"
                      >
                        {domain}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <MessageBubble
              key={msg.id}
              role={msg.role}
              content={msg.content}
              message_id={msg.message_id}
              citations={msg.citations}
              showCitations={showCitations}
            />
          )
        )}

        {isLoading && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-sm border border-gray-100 bg-white px-4 py-3 shadow-sm">
              <div className="flex items-center gap-1">
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-300 [animation-delay:0ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-300 [animation-delay:150ms]" />
                <span className="h-2 w-2 animate-bounce rounded-full bg-gray-300 [animation-delay:300ms]" />
              </div>
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>
    </div>
  );
}
