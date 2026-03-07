"use client";

/**
 * Admin — Performance Metrics Dashboard.
 *
 * Displays query performance data from GET /admin/metrics/summary
 * and feedback-based evaluation metrics from GET /admin/metrics/feedback-summary.
 *
 * Layout:
 *   ┌─ Header + time-window selector + Refresh button ───────────────────┐
 *   ├─ 4 stat cards: Total / Success Rate / Cross-Domain / Errors ────────┤
 *   ├─ Charts row: Query Distribution (donut) + Latency Breakdown (bar) ──┤
 *   ├─ Evaluation metrics: Accuracy / Weighted Precision / F1 ───────────┤
 *   ├─ Latency table (Embed / Retrieve / LLM / Total) ────────────────────┤
 *   ├─ Token usage stat cards ────────────────────────────────────────────┤
 *   └─ Retrieval stat card ───────────────────────────────────────────────┘
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const SYSTEM_ADMIN_ROLE_TYPE = "SYSTEM_ADMIN";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface LatencyStats {
  mean_ms: number;
  p50_ms: number;
  p95_ms: number;
  p99_ms: number;
  min_ms: number;
  max_ms: number;
}

interface MetricsSummary {
  total_queries: number;
  successful_queries: number;
  cross_domain_queries: number;
  error_queries: number;
  success_rate: number;
  cross_domain_rate: number;
  embed_latency: LatencyStats;
  retrieve_latency: LatencyStats;
  total_latency: LatencyStats;
  llm_latency: LatencyStats | null;
  avg_chunks_retrieved: number;
  avg_prompt_tokens: number;
  avg_completion_tokens: number;
  avg_total_tokens: number;
  window_start: string | null;
  window_end: string | null;
  computed_at: string;
}

interface FeedbackMetrics {
  total_rated: number;
  positive_count: number;
  negative_count: number;
  weighted_precision: number;
  avg_rating: number;
  weighted_avg_rating: number;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function clearMetrics(): Promise<void> {
  const res = await fetch("/api/backend/admin/metrics", {
    method: "DELETE",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to clear metrics");
  }
}

async function fetchMetrics(sinceHours: number): Promise<MetricsSummary> {
  const res = await fetch(
    `/api/backend/admin/metrics/summary?since_hours=${sinceHours}`,
    { credentials: "include" }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch metrics");
  }
  return res.json();
}

async function fetchFeedbackMetrics(): Promise<FeedbackMetrics> {
  const res = await fetch("/api/backend/admin/metrics/feedback-summary", {
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? "Failed to fetch feedback metrics");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Formatting helpers
// ---------------------------------------------------------------------------

function fmtMs(ms: number): string {
  return ms < 1000 ? `${ms.toFixed(1)} ms` : `${(ms / 1000).toFixed(2)} s`;
}

function fmtPct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  subtitle,
  highlight,
}: {
  label: string;
  value: string;
  subtitle?: string;
  highlight?: "green" | "red" | "amber";
}) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white px-5 py-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-gray-400">
        {label}
      </p>
      <p
        className={cn(
          "mt-1 text-2xl font-bold",
          highlight === "green" && "text-green-600",
          highlight === "red" && "text-red-600",
          highlight === "amber" && "text-amber-600",
          !highlight && "text-gray-900"
        )}
      >
        {value}
      </p>
      {subtitle && (
        <p className="mt-0.5 text-xs text-gray-400">{subtitle}</p>
      )}
    </div>
  );
}

function LatencyTable({ summary }: { summary: MetricsSummary }) {
  const rows: { label: string; stats: LatencyStats | null }[] = [
    { label: "Embed", stats: summary.embed_latency },
    { label: "Retrieve", stats: summary.retrieve_latency },
    { label: "LLM", stats: summary.llm_latency },
    { label: "Total", stats: summary.total_latency },
  ];

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
            <th className="px-4 py-3">Stage</th>
            <th className="px-4 py-3">Mean</th>
            <th className="px-4 py-3">P50</th>
            <th className="px-4 py-3">P95</th>
            <th className="px-4 py-3">P99</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {rows.map(({ label, stats }) => (
            <tr
              key={label}
              className={cn(
                "transition-colors hover:bg-gray-50",
                label === "Total" && "font-medium"
              )}
            >
              <td className="px-4 py-3 text-gray-700">{label}</td>
              {stats ? (
                <>
                  <td className="px-4 py-3 text-gray-900">{fmtMs(stats.mean_ms)}</td>
                  <td className="px-4 py-3 text-gray-900">{fmtMs(stats.p50_ms)}</td>
                  <td className="px-4 py-3 text-gray-900">{fmtMs(stats.p95_ms)}</td>
                  <td className="px-4 py-3 text-gray-900">{fmtMs(stats.p99_ms)}</td>
                </>
              ) : (
                <td className="px-4 py-3 text-gray-400 italic" colSpan={4}>
                  — not applicable (all queries were cross-domain)
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const DONUT_COLORS: Record<string, string> = {
  Successful: "#16a34a",
  "Cross-Domain": "#d97706",
  Errors: "#dc2626",
};

function QueryDistributionChart({ summary }: { summary: MetricsSummary }) {
  const data = [
    { name: "Successful", value: summary.successful_queries },
    { name: "Cross-Domain", value: summary.cross_domain_queries },
    { name: "Errors", value: summary.error_queries },
  ].filter((d) => d.value > 0);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <h3 className="mb-1 text-sm font-semibold text-gray-700">
        Query Outcome Distribution
      </h3>
      <p className="mb-4 text-xs text-gray-400">
        Breakdown of all queries in the selected window
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            innerRadius={55}
            outerRadius={85}
            paddingAngle={3}
            dataKey="value"
          >
            {data.map((entry) => (
              <Cell
                key={entry.name}
                fill={DONUT_COLORS[entry.name] ?? "#6b7280"}
              />
            ))}
          </Pie>
          <Tooltip />
          <Legend
            iconType="circle"
            iconSize={8}
            wrapperStyle={{ fontSize: "12px" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}

function LatencyBarChart({ summary }: { summary: MetricsSummary }) {
  const data = [
    { stage: "Embed", mean_ms: summary.embed_latency.mean_ms },
    { stage: "Retrieve", mean_ms: summary.retrieve_latency.mean_ms },
    ...(summary.llm_latency
      ? [{ stage: "LLM", mean_ms: summary.llm_latency.mean_ms }]
      : []),
    { stage: "Total", mean_ms: summary.total_latency.mean_ms },
  ];

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <h3 className="mb-1 text-sm font-semibold text-gray-700">
        Latency by Stage (mean)
      </h3>
      <p className="mb-4 text-xs text-gray-400">
        Average milliseconds per pipeline stage
      </p>
      <ResponsiveContainer width="100%" height={220}>
        <BarChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
          <XAxis
            dataKey="stage"
            tick={{ fontSize: 12, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            tickFormatter={(v: number) => (v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${v}ms`)}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            width={48}
          />
          <Tooltip
            formatter={(v: unknown) => [fmtMs(Number(v)), "Mean latency"]}
            cursor={{ fill: "#f9fafb" }}
          />
          <Bar dataKey="mean_ms" fill="#3b82f6" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function EvalMetricsSection({
  summary,
  feedback,
}: {
  summary: MetricsSummary;
  feedback: FeedbackMetrics | undefined;
}) {
  const accuracy = summary.success_rate; // 0–1
  const precision = feedback?.weighted_precision ?? null; // 0–1 or null if no data
  const hasFeedback = feedback && feedback.total_rated > 0;

  const f1 =
    hasFeedback && precision !== null && accuracy + precision > 0
      ? (2 * accuracy * precision) / (accuracy + precision)
      : null;

  return (
    <section>
      <div className="mb-3 flex items-baseline gap-2">
        <h2 className="text-base font-medium text-gray-700">
          Evaluation Metrics
        </h2>
        <span className="text-xs text-gray-400">
          Accuracy = query success rate · Precision = weighted user feedback · F1 = harmonic mean
        </span>
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <StatCard
          label="Accuracy"
          value={fmtPct(accuracy)}
          subtitle="Fraction of queries answered successfully"
          highlight={accuracy >= 0.9 ? "green" : accuracy >= 0.7 ? "amber" : "red"}
        />
        <StatCard
          label="Weighted Precision"
          value={hasFeedback && precision !== null ? fmtPct(precision) : "N/A"}
          subtitle={
            hasFeedback
              ? `Based on ${feedback!.total_rated} rated ${feedback!.total_rated === 1 ? "query" : "queries"}`
              : "No user feedback yet"
          }
          highlight={
            hasFeedback && precision !== null
              ? precision >= 0.8
                ? "green"
                : precision >= 0.6
                ? "amber"
                : "red"
              : undefined
          }
        />
        <StatCard
          label="F1 Score"
          value={f1 !== null ? fmtPct(f1) : "N/A"}
          subtitle="Harmonic mean of accuracy and precision"
          highlight={
            f1 !== null
              ? f1 >= 0.85
                ? "green"
                : f1 >= 0.65
                ? "amber"
                : "red"
              : undefined
          }
        />
      </div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

const WINDOW_OPTIONS = [
  { label: "Last 1 hour", value: 1 },
  { label: "Last 24 hours", value: 24 },
  { label: "Last 7 days", value: 168 },
  { label: "Last 30 days", value: 720 },
];

export default function MetricsPage() {
  const { user, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [sinceHours, setSinceHours] = useState(24);
  const [confirmClear, setConfirmClear] = useState(false);

  const isAdmin =
    user?.roles.some((r) => r.role_type === SYSTEM_ADMIN_ROLE_TYPE) ?? false;

  const { data, isLoading, isError, refetch, isFetching } =
    useQuery<MetricsSummary>({
      queryKey: ["admin", "metrics", sinceHours],
      queryFn: () => fetchMetrics(sinceHours),
      enabled: isAdmin,
    });

  const { data: feedbackData } = useQuery<FeedbackMetrics>({
    queryKey: ["admin", "metrics", "feedback"],
    queryFn: fetchFeedbackMetrics,
    enabled: isAdmin,
  });

  const clearMutation = useMutation({
    mutationFn: clearMetrics,
    onSuccess: () => {
      setConfirmClear(false);
      queryClient.invalidateQueries({ queryKey: ["admin", "metrics"] });
    },
    onError: () => setConfirmClear(false),
  });

  // ---------------------------------------------------------------------------
  // Auth guard
  // ---------------------------------------------------------------------------

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

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      {/* ── Header ──────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900">
            Performance Metrics
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Query latency, token usage, and success rates across the RAG pipeline.
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <select
            value={sinceHours}
            onChange={(e) => setSinceHours(Number(e.target.value))}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm text-gray-700 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-200"
          >
            {WINDOW_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => refetch()}
            disabled={isFetching}
            className={cn(
              "flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              "bg-blue-600 text-white hover:bg-blue-700",
              "disabled:cursor-not-allowed disabled:opacity-60"
            )}
          >
            {isFetching ? "Refreshing…" : "Refresh"}
          </button>
        </div>
      </div>

      {/* ── Error banner ──────────────────────────────────────────────── */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          Failed to load metrics. Make sure the API is running and you have run{" "}
          <code className="font-mono">alembic upgrade head</code>.
        </div>
      )}

      {/* ── Loading skeleton ───────────────────────────────────────────── */}
      {isLoading && (
        <div className="rounded-xl border border-gray-200 bg-white px-6 py-10 text-center">
          <p className="text-sm text-gray-500">Loading metrics…</p>
        </div>
      )}

      {/* ── Empty state ────────────────────────────────────────────────── */}
      {data && data.total_queries === 0 && (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white px-6 py-10 text-center">
          <p className="text-sm text-gray-500">
            No queries recorded in this time window. Submit a query via{" "}
            <strong>Chat</strong> and then refresh.
          </p>
        </div>
      )}

      {data && data.total_queries > 0 && (
        <>
          {/* ── Overview stat cards ─────────────────────────────────────── */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard
              label="Total Queries"
              value={String(data.total_queries)}
            />
            <StatCard
              label="Success Rate"
              value={fmtPct(data.success_rate)}
              highlight={data.success_rate >= 0.9 ? "green" : "red"}
            />
            <StatCard
              label="Cross-Domain"
              value={fmtPct(data.cross_domain_rate)}
            />
            <StatCard
              label="Errors"
              value={String(data.error_queries)}
              highlight={data.error_queries > 0 ? "red" : undefined}
            />
          </div>

          {/* ── Charts row ──────────────────────────────────────────────── */}
          <section>
            <h2 className="mb-3 text-base font-medium text-gray-700">
              Visualizations
            </h2>
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              <QueryDistributionChart summary={data} />
              <LatencyBarChart summary={data} />
            </div>
          </section>

          {/* ── Evaluation metrics ──────────────────────────────────────── */}
          <EvalMetricsSection summary={data} feedback={feedbackData} />

          {/* ── Latency breakdown table ──────────────────────────────────── */}
          <section>
            <h2 className="mb-3 text-base font-medium text-gray-700">
              Latency Breakdown
            </h2>
            <LatencyTable summary={data} />
          </section>

          {/* ── Token usage ─────────────────────────────────────────────── */}
          <section>
            <h2 className="mb-3 text-base font-medium text-gray-700">
              Token Usage (averages per query)
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
              <StatCard
                label="Avg Prompt Tokens"
                value={data.avg_prompt_tokens.toFixed(0)}
              />
              <StatCard
                label="Avg Completion Tokens"
                value={data.avg_completion_tokens.toFixed(0)}
              />
              <StatCard
                label="Avg Total Tokens"
                value={data.avg_total_tokens.toFixed(0)}
              />
            </div>
          </section>

          {/* ── Retrieval ───────────────────────────────────────────────── */}
          <section>
            <h2 className="mb-3 text-base font-medium text-gray-700">
              Retrieval
            </h2>
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              <StatCard
                label="Avg Chunks Retrieved"
                value={data.avg_chunks_retrieved.toFixed(1)}
              />
              <StatCard
                label="Successful Queries"
                value={`${data.successful_queries} / ${data.total_queries}`}
              />
            </div>
          </section>

          {/* ── Window footer ───────────────────────────────────────────── */}
          <p className="text-right text-xs text-gray-400">
            Data window:{" "}
            {data.window_start
              ? new Date(data.window_start).toLocaleString()
              : "—"}{" "}
            →{" "}
            {data.window_end
              ? new Date(data.window_end).toLocaleString()
              : "—"}
          </p>
        </>
      )}
    </div>
  );
}
