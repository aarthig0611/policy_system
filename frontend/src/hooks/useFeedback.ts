/**
 * useFeedback — Submits thumbs-up / thumbs-down feedback for an assistant message.
 *
 * Maps the boolean `is_positive` flag to the API's numeric rating field:
 *   thumbs-up  → rating 5
 *   thumbs-down → rating 1 (requires non-empty comment per backend validation)
 */

"use client";

import { useMutation } from "@tanstack/react-query";

interface FeedbackRequestBody {
  msg_id: string;
  rating: number;
  comments?: string;
}

interface FeedbackResponse {
  feedback_id: string;
  msg_id: string;
  rating: number;
  comments: string | null;
  weight: number;
  created_at: string;
}

async function postFeedback(body: FeedbackRequestBody): Promise<FeedbackResponse> {
  const res = await fetch("/api/backend/feedback/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Feedback submission failed" }));
    throw new Error(err.detail ?? "Feedback submission failed");
  }

  return res.json();
}

export function useFeedback() {
  const mutation = useMutation({
    mutationFn: postFeedback,
  });

  function submitFeedback(
    message_id: string,
    is_positive: boolean,
    comment?: string
  ) {
    mutation.mutate({
      msg_id: message_id,
      rating: is_positive ? 5 : 1,
      comments: comment,
    });
  }

  return {
    submitFeedback,
    isLoading: mutation.isPending,
    isSuccess: mutation.isSuccess,
    isError: mutation.isError,
    error: mutation.error,
    reset: mutation.reset,
  };
}
