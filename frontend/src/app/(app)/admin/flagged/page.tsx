"use client";

/**
 * Admin — Flagged Conversations page.
 *
 * Lists conversations where is_flagged=True.
 * Admin can resolve (unflag) each one individually.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const SYSTEM_ADMIN_ROLE_TYPE = "SYSTEM_ADMIN";

interface FlaggedConversation {
  conv_id: string;
  user_email: string;
  first_message: string | null;
  started_at: string;
  message_count: number;
}

async function fetchFlagged(): Promise<FlaggedConversation[]> {
  const res = await fetch("/api/backend/admin/flagged-conversations", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch flagged conversations");
  return res.json();
}

async function resolveConversation(convId: string): Promise<void> {
  const res = await fetch(
    `/api/backend/admin/flagged-conversations/${convId}`,
    { method: "PATCH", credentials: "include" }
  );
  if (!res.ok) throw new Error("Failed to resolve conversation");
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function FlaggedPage() {
  const { user, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const isAdmin =
    user?.roles.some((r) => r.role_type === SYSTEM_ADMIN_ROLE_TYPE) ?? false;

  const {
    data: conversations,
    isLoading,
    error,
  } = useQuery<FlaggedConversation[]>({
    queryKey: ["flagged-conversations"],
    queryFn: fetchFlagged,
    enabled: isAdmin,
  });

  const mutation = useMutation({
    mutationFn: resolveConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["flagged-conversations"] });
      setResolvingId(null);
    },
    onError: () => {
      setResolvingId(null);
    },
  });

  const handleResolve = (convId: string) => {
    setResolvingId(convId);
    mutation.mutate(convId);
  };

  if (authLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-gray-500">
        Loading…
      </div>
    );
  }

  if (!user || !isAdmin) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-gray-500">
        <h2 className="text-lg font-medium text-gray-700">Access denied</h2>
        <p className="mt-2 text-sm">
          You do not have permission to view this page.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">
          Flagged conversations
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Conversations flagged by the feedback system for review.
        </p>
      </div>

      {isLoading ? (
        <p className="text-sm text-gray-500">Loading…</p>
      ) : error ? (
        <p className="text-sm text-red-600">
          {error instanceof Error ? error.message : "An error occurred"}
        </p>
      ) : !conversations || conversations.length === 0 ? (
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-12 text-center">
          <p className="text-sm text-gray-500">No flagged conversations.</p>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">First message</th>
                <th className="px-4 py-3 whitespace-nowrap">Messages</th>
                <th className="px-4 py-3 whitespace-nowrap">Started</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {conversations.map((conv) => (
                <tr
                  key={conv.conv_id}
                  className="hover:bg-gray-50 transition-colors"
                >
                  <td className="px-4 py-3 font-medium text-gray-900">
                    {conv.user_email}
                  </td>
                  <td className="px-4 py-3 max-w-sm text-gray-600">
                    {conv.first_message ? (
                      <span className="line-clamp-2">{conv.first_message}</span>
                    ) : (
                      <span className="italic text-gray-400">No messages</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-gray-600">
                    {conv.message_count}
                  </td>
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {formatDate(conv.started_at)}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      type="button"
                      onClick={() => handleResolve(conv.conv_id)}
                      disabled={resolvingId === conv.conv_id}
                      className={cn(
                        "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                        "bg-green-600 text-white hover:bg-green-700",
                        "disabled:cursor-not-allowed disabled:opacity-50"
                      )}
                    >
                      {resolvingId === conv.conv_id ? "Resolving…" : "Resolve"}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
