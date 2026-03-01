"use client";

/**
 * FeedbackButtons — Thumbs-up / thumbs-down buttons for assistant messages.
 *
 * On thumbs-down, an inline comment textarea is revealed. The comment is
 * required before submission (the backend enforces rating < 3 requires comments).
 * After a successful submission, buttons are disabled and a confirmation is shown.
 */

import { useState } from "react";
import { useFeedback } from "@/hooks/useFeedback";
import { cn } from "@/lib/utils";

interface FeedbackButtonsProps {
  message_id: string;
}

export default function FeedbackButtons({ message_id }: FeedbackButtonsProps) {
  const [selected, setSelected] = useState<"up" | "down" | null>(null);
  const [comment, setComment] = useState("");
  const { submitFeedback, isLoading, isSuccess, isError, error, reset } = useFeedback();

  // Success: show a green confirmation — only after the API confirms
  if (isSuccess) {
    return (
      <div className="mt-1 flex items-center gap-1.5 text-xs text-green-600">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="13"
          height="13"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M20 6 9 17l-5-5" />
        </svg>
        Feedback received
      </div>
    );
  }

  function handleThumbsUp() {
    if (isLoading) return;
    setSelected("up");
    submitFeedback(message_id, true);
  }

  function handleThumbsDownSelect() {
    if (isLoading) return;
    setSelected("down");
  }

  function handleThumbsDownSubmit() {
    if (!comment.trim() || isLoading) return;
    submitFeedback(message_id, false, comment.trim());
  }

  function handleRetry() {
    reset();
    setSelected(null);
    setComment("");
  }

  return (
    <div className="mt-2 space-y-2">
      <div className="flex items-center gap-2">
        {/* Thumbs up */}
        <button
          type="button"
          onClick={handleThumbsUp}
          disabled={isLoading || selected !== null}
          aria-label="Thumbs up"
          className={cn(
            "rounded p-1 transition-colors",
            selected === "up"
              ? "text-green-500"
              : "text-gray-400 hover:text-green-500 disabled:cursor-not-allowed disabled:opacity-40"
          )}
        >
          {isLoading && selected === "up" ? (
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
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
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M7 10v12" />
              <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H4a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12 2a3.13 3.13 0 0 1 3 3.88Z" />
            </svg>
          )}
        </button>

        {/* Thumbs down */}
        <button
          type="button"
          onClick={handleThumbsDownSelect}
          disabled={isLoading || selected === "up"}
          aria-label="Thumbs down"
          className={cn(
            "rounded p-1 transition-colors",
            selected === "down"
              ? "text-red-500"
              : "text-gray-400 hover:text-red-500 disabled:cursor-not-allowed disabled:opacity-40"
          )}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M17 14V2" />
            <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H20a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L12 22a3.13 3.13 0 0 1-3-3.88Z" />
          </svg>
        </button>
      </div>

      {/* Thumbs-down comment form */}
      {selected === "down" && !isError && (
        <div className="space-y-1.5">
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            placeholder="Please describe the issue (required)"
            rows={2}
            className={cn(
              "w-full resize-none rounded-md border border-gray-200 px-2 py-1.5 text-xs",
              "outline-none transition-colors focus:border-blue-400 focus:ring-1 focus:ring-blue-200"
            )}
            aria-label="Feedback comment"
          />
          <button
            type="button"
            onClick={handleThumbsDownSubmit}
            disabled={!comment.trim() || isLoading}
            className={cn(
              "rounded-md bg-red-50 px-3 py-1 text-xs font-medium text-red-700 transition-colors",
              "hover:bg-red-100 disabled:cursor-not-allowed disabled:opacity-50"
            )}
          >
            {isLoading ? "Submitting…" : "Submit"}
          </button>
        </div>
      )}

      {/* Error state with retry */}
      {isError && (
        <div className="flex items-center gap-2">
          <p className="text-xs text-red-500">
            {error instanceof Error ? error.message : "Feedback failed"}
          </p>
          <button
            type="button"
            onClick={handleRetry}
            className="text-xs font-medium text-red-600 underline hover:text-red-800"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}
