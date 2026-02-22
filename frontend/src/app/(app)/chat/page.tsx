"use client";

/**
 * Chat page — main interface for policy Q&A.
 *
 * Manages session-level state:
 *   - response format (summary | detailed)
 *   - domain filter (null = all domains)
 *   - include_archived toggle
 *   - query input text
 *
 * Composes MessageThread, FormatToggle, DomainSelector, ArchiveToggle,
 * and CrossDomainPrompt.
 */

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { useAuth } from "@/hooks/useAuth";
import { useChat } from "@/hooks/useChat";
import MessageThread from "@/components/chat/MessageThread";
import FormatToggle, { ResponseFormat } from "@/components/chat/FormatToggle";
import DomainSelector from "@/components/chat/DomainSelector";
import ArchiveToggle from "@/components/chat/ArchiveToggle";
import CrossDomainPrompt from "@/components/chat/CrossDomainPrompt";
import { cn } from "@/lib/utils";

/** Extract unique non-null domains from the user's roles. */
function extractDomains(
  roles: Array<{ domain: string | null }>
): string[] {
  const seen = new Set<string>();
  for (const role of roles) {
    if (role.domain != null && role.domain !== "") {
      seen.add(role.domain);
    }
  }
  return Array.from(seen).sort();
}

export default function ChatPage() {
  const { user } = useAuth();

  // Session-level controls
  const [format, setFormat] = useState<ResponseFormat>("summary");
  const [domainFilter, setDomainFilter] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);

  // Query input
  const [inputText, setInputText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    isLoading,
    error,
    crossDomainOpen,
    crossDomainMessage,
    sendQuery,
    closeCrossDomainPrompt,
  } = useChat();

  const domains = user ? extractDomains(user.roles) : [];

  const handleSend = useCallback(() => {
    const text = inputText.trim();
    if (!text || isLoading) return;

    sendQuery(text, {
      format,
      domain_filter: domainFilter,
      include_archived: includeArchived,
    });

    setInputText("");
    // Reset textarea height after clearing
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  }, [inputText, isLoading, sendQuery, format, domainFilter, includeArchived]);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    // Submit on Enter without Shift (Shift+Enter = newline)
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInputText(e.target.value);
    // Auto-grow textarea up to ~6 lines
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  const showCitations = format === "detailed";

  return (
    <>
      {/* CrossDomainPrompt modal */}
      <CrossDomainPrompt
        open={crossDomainOpen}
        message={crossDomainMessage}
        onClose={closeCrossDomainPrompt}
      />

      {/*
        The (app) layout already provides a top Navbar.
        We override the default padding by using negative margin trick,
        then build a full-height flex column for the chat UI.
      */}
      <div className="-m-6 flex h-[calc(100vh-3.5rem)] flex-col bg-gray-50">
        {/* Message area */}
        <MessageThread
          messages={messages}
          showCitations={showCitations}
          isLoading={isLoading}
        />

        {/* Error banner */}
        {error && (
          <div className="border-t border-red-100 bg-red-50 px-4 py-2 text-center text-sm text-red-700">
            {error instanceof Error ? error.message : "An error occurred"}
          </div>
        )}

        {/* Fixed input area */}
        <div className="border-t border-gray-200 bg-white px-4 pb-4 pt-3">
          <div className="mx-auto w-full max-w-3xl space-y-2">
            {/* Controls row */}
            <div className="flex flex-wrap items-center gap-3">
              <FormatToggle value={format} onChange={setFormat} />
              {domains.length > 1 && (
                <DomainSelector
                  domains={domains}
                  value={domainFilter}
                  onChange={setDomainFilter}
                />
              )}
              <ArchiveToggle value={includeArchived} onChange={setIncludeArchived} />
            </div>

            {/* Textarea + Send */}
            <div className="flex items-end gap-2">
              <textarea
                ref={textareaRef}
                value={inputText}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="Ask a policy question… (Enter to send, Shift+Enter for newline)"
                rows={1}
                disabled={isLoading}
                className={cn(
                  "flex-1 resize-none rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 text-sm",
                  "leading-relaxed outline-none transition-colors",
                  "focus:border-blue-400 focus:bg-white focus:ring-1 focus:ring-blue-200",
                  "disabled:cursor-not-allowed disabled:opacity-60",
                  "placeholder:text-gray-400"
                )}
                aria-label="Policy question"
              />
              <button
                type="button"
                onClick={handleSend}
                disabled={!inputText.trim() || isLoading}
                className={cn(
                  "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl",
                  "bg-blue-600 text-white transition-colors",
                  "hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300",
                  "disabled:cursor-not-allowed disabled:opacity-50"
                )}
                aria-label="Send message"
              >
                {isLoading ? (
                  /* Spinner */
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    className="animate-spin"
                    aria-hidden="true"
                  >
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                ) : (
                  /* Send arrow */
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    width="18"
                    height="18"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <line x1="22" x2="11" y1="2" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
