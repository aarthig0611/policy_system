/**
 * useChat — Manages conversation state and query submission.
 *
 * Maintains the local list of messages and the current conversation_id.
 * Sends queries via POST /api/backend/query/ and appends both the user
 * message and the assistant response (or cross-domain prompt signal) to state.
 */

"use client";

import { useState, useCallback } from "react";
import { useMutation } from "@tanstack/react-query";

export interface Citation {
  doc_id: string;
  doc_title: string;
  page_number: number | null;
  para_number: number | null;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  message_id?: string;
  citations?: Citation[];
  availableDomains?: string[]; // set on the inline cross-domain prompt message
}

export interface SendQueryOptions {
  format: "summary" | "detailed";
  domain_filter: string | null;
  include_archived: boolean;
}

interface QueryRequestBody {
  message: string;
  format_override: "EXECUTIVE_SUMMARY" | "DETAILED_RESPONSE" | null;
  include_archived: boolean;
  domain_filter: string | null;
  conv_id: string | null;
}

interface QueryResponse {
  msg_id: string;
  conv_id: string;
  content: string;
  format_used: string;
  citations: Citation[];
  retrieved_doc_ids: string[];
}

interface CrossDomainResponse {
  type: "cross_domain_permission_required";
  message: string;
  available_domains: string[];
}

async function postQuery(
  body: QueryRequestBody
): Promise<QueryResponse | CrossDomainResponse> {
  const res = await fetch("/api/backend/query/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(err.detail ?? "Query failed");
  }

  return res.json();
}

function generateLocalId(): string {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export function useChat() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [lastQueryText, setLastQueryText] = useState<string | null>(null);
  const [lastQueryOptions, setLastQueryOptions] = useState<SendQueryOptions | null>(null);

  const mutation = useMutation({
    mutationFn: postQuery,
    onSuccess: (data, variables) => {
      if ("type" in data && data.type === "cross_domain_permission_required") {
        // Replace the pending user message with an inline domain-switch card
        setMessages((prev) => [
          ...prev.slice(0, -1),
          {
            id: generateLocalId(),
            role: "assistant",
            content: data.message,
            availableDomains: data.available_domains,
          },
        ]);
        return;
      }

      const response = data as QueryResponse;

      // Persist conversation ID for follow-up turns
      if (!conversationId) {
        setConversationId(response.conv_id);
      }

      const isDetailed =
        response.format_used === "DETAILED_RESPONSE" &&
        variables.format_override === "DETAILED_RESPONSE";

      const assistantMessage: ChatMessage = {
        id: generateLocalId(),
        role: "assistant",
        content: response.content,
        message_id: response.msg_id,
        citations: isDetailed ? response.citations : [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    },
  });

  const sendQuery = useCallback(
    (text: string, options: SendQueryOptions) => {
      setLastQueryText(text);
      setLastQueryOptions(options);

      const userMessage: ChatMessage = {
        id: generateLocalId(),
        role: "user",
        content: text,
      };

      setMessages((prev) => [...prev, userMessage]);

      mutation.mutate({
        message: text,
        format_override:
          options.format === "detailed"
            ? "DETAILED_RESPONSE"
            : "EXECUTIVE_SUMMARY",
        include_archived: options.include_archived,
        domain_filter: options.domain_filter,
        conv_id: conversationId,
      });
    },
    [mutation, conversationId]
  );

  /** Re-send the last query with a new domain filter (after a cross-domain prompt). */
  const retryWithDomain = useCallback(
    (domain: string) => {
      if (!lastQueryText || !lastQueryOptions) return;

      const newOptions = { ...lastQueryOptions, domain_filter: domain };
      setLastQueryOptions(newOptions);

      // Remove the cross-domain inline message and re-add the user message
      const userMessage: ChatMessage = {
        id: generateLocalId(),
        role: "user",
        content: lastQueryText,
      };
      setMessages((prev) => [
        ...prev.filter((m) => !m.availableDomains),
        userMessage,
      ]);

      mutation.mutate({
        message: lastQueryText,
        format_override:
          newOptions.format === "detailed"
            ? "DETAILED_RESPONSE"
            : "EXECUTIVE_SUMMARY",
        include_archived: newOptions.include_archived,
        domain_filter: domain,
        conv_id: conversationId,
      });
    },
    [lastQueryText, lastQueryOptions, mutation, conversationId]
  );

  const resetConversation = useCallback(() => {
    setMessages([]);
    setConversationId(null);
  }, []);

  /** Load a historical conversation into the current chat state. */
  const loadConversation = useCallback(
    (convId: string, historicalMessages: ChatMessage[]) => {
      setMessages(historicalMessages);
      setConversationId(convId);
    },
    []
  );

  return {
    messages,
    conversationId,
    isLoading: mutation.isPending,
    error: mutation.error,
    sendQuery,
    retryWithDomain,
    resetConversation,
    loadConversation,
  };
}
