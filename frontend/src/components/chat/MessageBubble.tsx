"use client";

/**
 * MessageBubble — Renders a single chat message.
 *
 * User messages: right-aligned with muted background.
 * Assistant messages: left-aligned with white/card background, optional
 *   citations (Detailed mode) and feedback buttons.
 */

import { cn } from "@/lib/utils";
import CitationBlock from "@/components/chat/CitationBlock";
import FeedbackButtons from "@/components/chat/FeedbackButtons";
import type { Citation } from "@/hooks/useChat";

interface MessageBubbleProps {
  role: "user" | "assistant";
  content: string;
  message_id?: string;
  citations?: Citation[];
  showCitations: boolean;
}

export default function MessageBubble({
  role,
  content,
  message_id,
  citations,
  showCitations,
}: MessageBubbleProps) {
  const isUser = role === "user";

  return (
    <div
      className={cn(
        "flex w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser
            ? "rounded-br-sm bg-blue-600 text-white"
            : "rounded-bl-sm border border-gray-100 bg-white text-gray-800 shadow-sm"
        )}
      >
        <p className="whitespace-pre-wrap break-words">{content}</p>

        {!isUser && showCitations && citations && citations.length > 0 && (
          <CitationBlock citations={citations} />
        )}

        {!isUser && message_id && (
          <FeedbackButtons message_id={message_id} />
        )}
      </div>
    </div>
  );
}
