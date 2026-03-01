"use client";

/**
 * useConversations — fetches the current user's conversation history.
 *
 * Provides:
 *   - conversations: list ordered newest-first
 *   - fetchMessages: load messages for a specific conversation
 */

import { useQuery } from "@tanstack/react-query";

export interface ConversationSummary {
  conv_id: string;
  user_id: string;
  is_flagged: boolean;
  started_at: string; // ISO string
  message_count: number;
}

export interface HistoricalMessage {
  msg_id: string;
  conv_id: string;
  role: "user" | "assistant";
  content: string;
  format_used: string;
  created_at: string;
}

async function fetchConversations(): Promise<ConversationSummary[]> {
  const res = await fetch("/api/backend/query/conversations", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export async function fetchConversationMessages(
  convId: string
): Promise<HistoricalMessage[]> {
  const res = await fetch(
    `/api/backend/query/conversations/${convId}/messages`,
    { credentials: "include" }
  );
  if (!res.ok) throw new Error("Failed to fetch conversation messages");
  return res.json();
}

export function useConversations() {
  const { data, isLoading, error, refetch } = useQuery<ConversationSummary[]>({
    queryKey: ["conversations"],
    queryFn: fetchConversations,
    staleTime: 30_000, // re-fetch after 30s
  });

  return {
    conversations: data ?? [],
    isLoading,
    error,
    refetch,
  };
}
