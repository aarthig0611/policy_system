"use client";

/**
 * Admin Dashboard — overview summary cards for Metrics, Feedback, Validation,
 * and Flagged. "View all →" renders the existing full page component inline
 * with a "← Back to Dashboard" button, reusing code without duplication.
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";
import MetricsPage from "./metrics/page";
import ValidationPage from "./validation/page";
import FlaggedPage from "./flagged/page";

const SYSTEM_ADMIN_ROLE_TYPE = "SYSTEM_ADMIN";

type ActiveView = "overview" | "metrics" | "validation" | "flagged";

// ── Types (overview only) ─────────────────────────────────────────────────────

interface MetricsSummary {
  total_queries: number;
  success_rate: number;
  total_latency: { mean_ms: number };
}

interface FeedbackMetrics {
  positive_count: number;
  negative_count: number;
  weighted_precision: number;
}

interface ValidationSummary {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
}

interface FlaggedConversation {
  conv_id: string;
  user_email: string;
  first_message: string | null;
  started_at: string;
  message_count: number;
  feedback_comment: string | null;
}

// ── Fetch helpers (overview only) ─────────────────────────────────────────────

async function fetchMetrics(): Promise<MetricsSummary> {
  const res = await fetch(
    "/api/backend/admin/metrics/summary?since_hours=24",
    { credentials: "include" }
  );
  if (!res.ok) throw new Error("Failed to fetch metrics");
  return res.json();
}

async function fetchFeedback(): Promise<FeedbackMetrics> {
  const res = await fetch("/api/backend/admin/metrics/feedback-summary", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch feedback metrics");
  return res.json();
}

async function fetchValidationSummary(): Promise<ValidationSummary | null> {
  const res = await fetch("/api/backend/validation/run/summary", {
    credentials: "include",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch validation summary");
  return res.json();
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

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtPct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function fmtMs(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}s` : `${n.toFixed(0)}ms`;
}

// ── Shared UI ─────────────────────────────────────────────────────────────────

function SectionCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-gray-200 bg-white p-5",
        className
      )}
    >
      {children}
    </div>
  );
}

function SectionHeader({
  title,
  badge,
  onViewAll,
}: {
  title: string;
  badge?: number;
  onViewAll: () => void;
}) {
  return (
    <div className="mb-4 flex items-center justify-between">
      <div className="flex items-center gap-2">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-500">
          {title}
        </h2>
        {badge != null && badge > 0 && (
          <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
            {badge}
          </span>
        )}
      </div>
      <button
        type="button"
        onClick={onViewAll}
        className="text-xs text-indigo-600 hover:text-indigo-800 hover:underline"
      >
        View all →
      </button>
    </div>
  );
}

function LoadingState() {
  return <p className="text-sm text-gray-400">Loading…</p>;
}

function ErrorState({ error }: { error: unknown }) {
  return (
    <p className="text-sm text-red-600">
      {error instanceof Error ? error.message : "Failed to load"}
    </p>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const { user, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [activeView, setActiveView] = useState<ActiveView>("overview");

  const isAdmin =
    user?.roles.some((r) => r.role_type === SYSTEM_ADMIN_ROLE_TYPE) ?? false;

  const metricsQ = useQuery<MetricsSummary>({
    queryKey: ["dashboard-metrics"],
    queryFn: fetchMetrics,
    enabled: isAdmin,
  });
  const feedbackQ = useQuery<FeedbackMetrics>({
    queryKey: ["dashboard-feedback"],
    queryFn: fetchFeedback,
    enabled: isAdmin,
  });
  const validationQ = useQuery<ValidationSummary | null>({
    queryKey: ["dashboard-validation"],
    queryFn: fetchValidationSummary,
    enabled: isAdmin,
    retry: false,
  });
  const flaggedQ = useQuery<FlaggedConversation[]>({
    queryKey: ["dashboard-flagged"],
    queryFn: fetchFlagged,
    enabled: isAdmin,
  });

  const resolveMutation = useMutation({
    mutationFn: resolveConversation,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard-flagged"] });
      queryClient.invalidateQueries({ queryKey: ["flagged-conversations"] });
      setResolvingId(null);
    },
    onError: () => setResolvingId(null),
  });

  const handleResolve = (convId: string) => {
    setResolvingId(convId);
    resolveMutation.mutate(convId);
  };

  // ── Auth guard ────────────────────────────────────────────────────────────

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

  // ── Detail views — render existing page components directly ───────────────

  if (activeView !== "overview") {
    return (
      <>
        <div className="mx-auto max-w-5xl mb-4">
          <button
            type="button"
            onClick={() => setActiveView("overview")}
            className="flex items-center gap-1 text-sm text-gray-500 transition-colors hover:text-gray-900"
          >
            ← Back to Dashboard
          </button>
        </div>
        {activeView === "metrics" && <MetricsPage />}
        {activeView === "validation" && <ValidationPage />}
        {activeView === "flagged" && <FlaggedPage />}
      </>
    );
  }

  // ── Overview ──────────────────────────────────────────────────────────────

  const flagged = flaggedQ.data ?? [];
  const top3 = flagged.slice(0, 3);

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">
          Admin Dashboard
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Overview of system activity and alerts.
        </p>
      </div>

      {/* Metrics + Feedback */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <SectionCard>
          <SectionHeader
            title="Metrics (24h)"
            onViewAll={() => setActiveView("metrics")}
          />
          {metricsQ.isLoading ? (
            <LoadingState />
          ) : metricsQ.error ? (
            <ErrorState error={metricsQ.error} />
          ) : metricsQ.data ? (
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {metricsQ.data.total_queries}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">Total queries</p>
              </div>
              <div>
                <p
                  className={cn(
                    "text-2xl font-bold",
                    metricsQ.data.success_rate >= 0.9
                      ? "text-green-600"
                      : "text-red-600"
                  )}
                >
                  {fmtPct(metricsQ.data.success_rate)}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">Success rate</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-gray-900">
                  {fmtMs(metricsQ.data.total_latency.mean_ms)}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">Avg latency</p>
              </div>
            </div>
          ) : null}
        </SectionCard>

        <SectionCard>
          <SectionHeader
            title="Feedback"
            onViewAll={() => setActiveView("metrics")}
          />
          {feedbackQ.isLoading ? (
            <LoadingState />
          ) : feedbackQ.error ? (
            <ErrorState error={feedbackQ.error} />
          ) : feedbackQ.data ? (
            <div className="grid grid-cols-3 gap-4">
              <div>
                <p
                  className={cn(
                    "text-2xl font-bold",
                    feedbackQ.data.weighted_precision >= 0.8
                      ? "text-green-600"
                      : feedbackQ.data.weighted_precision >= 0.6
                      ? "text-amber-600"
                      : "text-red-600"
                  )}
                >
                  {fmtPct(feedbackQ.data.weighted_precision)}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">
                  Weighted precision
                </p>
              </div>
              <div>
                <p className="text-2xl font-bold text-green-600">
                  {feedbackQ.data.positive_count}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">Positive</p>
              </div>
              <div>
                <p className="text-2xl font-bold text-red-600">
                  {feedbackQ.data.negative_count}
                </p>
                <p className="mt-0.5 text-xs text-gray-500">Negative</p>
              </div>
            </div>
          ) : null}
        </SectionCard>
      </div>

      {/* Validation */}
      <SectionCard>
        <SectionHeader
          title="Validation (latest run)"
          onViewAll={() => setActiveView("validation")}
        />
        {validationQ.isLoading ? (
          <LoadingState />
        ) : validationQ.error ? (
          <ErrorState error={validationQ.error} />
        ) : validationQ.data ? (
          <div className="grid grid-cols-5 gap-4">
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {validationQ.data.total}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Total</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-green-600">
                {validationQ.data.passed}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Passed</p>
            </div>
            <div>
              <p
                className={cn(
                  "text-2xl font-bold",
                  validationQ.data.failed > 0 ? "text-red-600" : "text-gray-900"
                )}
              >
                {validationQ.data.failed}
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Failed</p>
            </div>
            <div>
              <p
                className={cn(
                  "text-2xl font-bold",
                  validationQ.data.pass_rate >= 0.7
                    ? "text-green-600"
                    : "text-red-600"
                )}
              >
                {(validationQ.data.pass_rate * 100).toFixed(0)}%
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Pass rate</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900">
                {(validationQ.data.avg_score * 100).toFixed(0)}%
              </p>
              <p className="mt-0.5 text-xs text-gray-500">Avg score</p>
            </div>
          </div>
        ) : (
          <p className="text-sm text-gray-400">No runs yet.</p>
        )}
      </SectionCard>

      {/* Flagged conversations */}
      <div>
        <SectionHeader
          title="Flagged Conversations"
          badge={flagged.length}
          onViewAll={() => setActiveView("flagged")}
        />
        {flaggedQ.isLoading ? (
          <SectionCard>
            <LoadingState />
          </SectionCard>
        ) : flaggedQ.error ? (
          <SectionCard>
            <ErrorState error={flaggedQ.error} />
          </SectionCard>
        ) : flagged.length === 0 ? (
          <SectionCard>
            <p className="text-center text-sm text-gray-500">
              No flagged conversations.
            </p>
          </SectionCard>
        ) : (
          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">First message</th>
                  <th className="px-4 py-3">Feedback</th>
                  <th className="px-4 py-3"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {top3.map((conv) => (
                  <tr
                    key={conv.conv_id}
                    className="transition-colors hover:bg-gray-50"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900">
                      {conv.user_email}
                    </td>
                    <td className="max-w-xs px-4 py-3 text-gray-600">
                      {conv.first_message ? (
                        <span className="line-clamp-1">
                          {conv.first_message}
                        </span>
                      ) : (
                        <span className="italic text-gray-400">No messages</span>
                      )}
                    </td>
                    <td className="max-w-xs px-4 py-3 text-gray-600">
                      {conv.feedback_comment ? (
                        <span className="line-clamp-1 text-red-700">
                          {conv.feedback_comment}
                        </span>
                      ) : (
                        <span className="italic text-gray-400">—</span>
                      )}
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
    </div>
  );
}
