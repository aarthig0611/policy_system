"use client";

/**
 * Chat page — main interface for policy Q&A.
 *
 * Layout:
 *   ┌──────────────┬──────────────────────────────────┐
 *   │  Sidebar     │  Message thread + input bar      │
 *   │  (past convs)│                                  │
 *   └──────────────┴──────────────────────────────────┘
 *
 * Sidebar lists past conversations. Clicking one loads its messages.
 * "New chat" button starts a fresh conversation.
 */

import { useState, useRef, useCallback, KeyboardEvent } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { useChat, type ChatMessage } from "@/hooks/useChat";
import {
  useConversations,
  fetchConversationMessages,
  type ConversationSummary,
} from "@/hooks/useConversations";
import MessageThread from "@/components/chat/MessageThread";
import FormatToggle, { ResponseFormat } from "@/components/chat/FormatToggle";
import DomainSelector from "@/components/chat/DomainSelector";
import ArchiveToggle from "@/components/chat/ArchiveToggle";
import { cn } from "@/lib/utils";

/** Extract unique non-null domains from the user's roles. */
function extractDomains(roles: Array<{ domain: string | null }>): string[] {
  const seen = new Set<string>();
  for (const role of roles) {
    if (role.domain != null && role.domain !== "") seen.add(role.domain);
  }
  return Array.from(seen).sort();
}

/** Format ISO timestamp as a short relative label. */
function formatRelativeDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / 86_400_000);
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

// ---------------------------------------------------------------------------
// Conversation sidebar item
// ---------------------------------------------------------------------------

function ConvItem({
  conv,
  isActive,
  onClick,
}: {
  conv: ConversationSummary;
  isActive: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full rounded-lg px-3 py-2.5 text-left transition-colors",
        isActive
          ? "bg-blue-50 text-blue-900"
          : "text-gray-700 hover:bg-gray-100"
      )}
    >
      <div className="flex items-center justify-between gap-1">
        <span className="truncate text-xs font-medium">
          {formatRelativeDate(conv.started_at)}
        </span>
        {conv.is_flagged && (
          <span className="shrink-0 rounded bg-red-100 px-1 py-0.5 text-[10px] font-semibold text-red-600">
            flagged
          </span>
        )}
      </div>
      <p className="mt-0.5 truncate text-xs text-gray-400">
        {conv.first_user_message ?? `${conv.message_count} message${conv.message_count !== 1 ? "s" : ""}`}
      </p>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function ChatPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Session-level controls
  const [format, setFormat] = useState<ResponseFormat>("summary");
  const [domainFilter, setDomainFilter] = useState<string | null>(null);
  const [includeArchived, setIncludeArchived] = useState(false);

  // Sidebar toggle (mobile)
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Which conv is loaded (for sidebar highlight)
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [loadingConvId, setLoadingConvId] = useState<string | null>(null);

  // Query input
  const [inputText, setInputText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const {
    messages,
    conversationId,
    isLoading,
    error,
    sendQuery,
    retryWithDomain,
    resetConversation,
    loadConversation,
  } = useChat();

  const { conversations, isLoading: convsLoading } = useConversations();
  const domains = user ? extractDomains(user.roles) : [];

  // Load a past conversation into the chat
  const handleSelectConversation = useCallback(
    async (conv: ConversationSummary) => {
      if (loadingConvId) return;
      setLoadingConvId(conv.conv_id);
      setSidebarOpen(false);
      try {
        const msgs = await fetchConversationMessages(conv.conv_id);
        const chatMessages: ChatMessage[] = msgs.map((m) => ({
          id: m.msg_id,
          role: m.role,
          content: m.content,
          message_id: m.role === "assistant" ? m.msg_id : undefined,
        }));
        loadConversation(conv.conv_id, chatMessages);
        setActiveConvId(conv.conv_id);
      } finally {
        setLoadingConvId(null);
      }
    },
    [loadConversation, loadingConvId]
  );

  const handleNewChat = useCallback(() => {
    resetConversation();
    setActiveConvId(null);
    setSidebarOpen(false);
  }, [resetConversation]);

  const handleDomainSwitch = useCallback(
    (domain: string) => {
      setDomainFilter(domain);
      retryWithDomain(domain);
    },
    [retryWithDomain]
  );

  const handleSend = useCallback(() => {
    const text = inputText.trim();
    if (!text || isLoading) return;

    sendQuery(text, {
      format,
      domain_filter: domainFilter,
      include_archived: includeArchived,
    });

    setInputText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    // After sending, refresh conversation list so message_count updates
    queryClient.invalidateQueries({ queryKey: ["conversations"] });
  }, [
    inputText,
    isLoading,
    sendQuery,
    format,
    domainFilter,
    includeArchived,
    queryClient,
  ]);

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleTextareaChange(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInputText(e.target.value);
    const el = e.target;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }

  const showCitations = format === "detailed";

  // Sync active conv ID when a new conversation is started via sendQuery
  const displayedConvId = conversationId ?? activeConvId;

  return (
    <>
      {/* Full-height flex row overriding default layout padding */}
      <div className="-m-6 flex h-[calc(100vh-3.5rem)]">
        {/* ── Sidebar ─────────────────────────────────────── */}
        {/* Overlay for mobile */}
        {sidebarOpen && (
          <div
            className="fixed inset-0 z-20 bg-black/30 md:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}

        <aside
          className={cn(
            "fixed inset-y-14 left-0 z-30 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform md:static md:inset-auto md:translate-x-0 md:z-auto",
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          )}
        >
          {/* Sidebar header */}
          <div className="flex items-center justify-between border-b border-gray-100 px-3 py-3">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">
              History
            </span>
            <button
              type="button"
              onClick={handleNewChat}
              className={cn(
                "rounded-md bg-blue-600 px-2.5 py-1 text-xs font-medium text-white",
                "transition-colors hover:bg-blue-700"
              )}
            >
              + New chat
            </button>
          </div>

          {/* Conversation list */}
          <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
            {convsLoading ? (
              <p className="px-2 py-4 text-center text-xs text-gray-400">
                Loading…
              </p>
            ) : conversations.length === 0 ? (
              <p className="px-2 py-4 text-center text-xs text-gray-400">
                No conversations yet.
              </p>
            ) : (
              conversations.map((conv) => (
                <ConvItem
                  key={conv.conv_id}
                  conv={conv}
                  isActive={conv.conv_id === displayedConvId}
                  onClick={() => handleSelectConversation(conv)}
                />
              ))
            )}
          </div>
        </aside>

        {/* ── Main chat area ──────────────────────────────── */}
        <div className="flex flex-1 flex-col overflow-hidden bg-gray-50">
          {/* Mobile top bar with hamburger */}
          <div className="flex items-center gap-2 border-b border-gray-200 bg-white px-4 py-2 md:hidden">
            <button
              type="button"
              onClick={() => setSidebarOpen(true)}
              className="rounded-md p-1.5 text-gray-500 hover:bg-gray-100"
              aria-label="Open conversation history"
            >
              {/* Hamburger icon */}
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
            <span className="text-sm font-medium text-gray-700">
              {displayedConvId ? "Conversation" : "New chat"}
            </span>
          </div>

          {/* Messages */}
          <MessageThread
            messages={messages}
            showCitations={showCitations}
            isLoading={isLoading || loadingConvId !== null}
            onDomainSwitch={handleDomainSwitch}
          />

          {/* Error banner */}
          {error && (
            <div className="border-t border-red-100 bg-red-50 px-4 py-2 text-center text-sm text-red-700">
              {error instanceof Error ? error.message : "An error occurred"}
            </div>
          )}

          {/* Input area */}
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
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="animate-spin" aria-hidden="true">
                      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                    </svg>
                  ) : (
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                      <line x1="22" x2="11" y1="2" y2="13" />
                      <polygon points="22 2 15 22 11 13 2 9" />
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
