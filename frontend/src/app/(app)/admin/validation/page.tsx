"use client";

/**
 * Admin — Validation Dashboard.
 *
 * Lets admins (SYSTEM_ADMIN) trigger the QA harness and review results.
 *
 * Layout:
 *   ┌─ Header + Run button ───────────────────────────────────┐
 *   ├─ Summary stats (total / passed / failed / rate / score) ┤
 *   ├─ Latest batch results table ───────────────────────────┤
 *   └─ Gold standards reference table ───────────────────────┘
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const SYSTEM_ADMIN_ROLE_TYPE = "SYSTEM_ADMIN";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ValidationRun {
  run_id: string;
  question_id: string;
  ai_answer: string;
  similarity_score: number;
  passed: boolean;
  model_name: string;
  run_at: string;
}

interface GoldQuestion {
  question_id: string;
  question_text: string;
  gold_answer: string;
  domain: string | null;
  created_at: string;
}

interface ValidationSummary {
  total: number;
  passed: number;
  failed: number;
  pass_rate: number;
  avg_score: number;
}

// ---------------------------------------------------------------------------
// API helpers
// ---------------------------------------------------------------------------

async function fetchSummary(): Promise<ValidationSummary | null> {
  const res = await fetch("/api/backend/validation/run/summary", {
    credentials: "include",
  });
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch summary");
  return res.json();
}

async function fetchRuns(): Promise<ValidationRun[]> {
  const res = await fetch("/api/backend/validation/runs", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch runs");
  return res.json();
}

async function fetchGold(): Promise<GoldQuestion[]> {
  const res = await fetch("/api/backend/validation/gold", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch gold standards");
  return res.json();
}

async function triggerRun(): Promise<ValidationRun[]> {
  const res = await fetch("/api/backend/validation/run", {
    method: "POST",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Run failed" }));
    throw new Error(err.detail ?? "Validation run failed");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatCard({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string;
  highlight?: "green" | "red";
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
          !highlight && "text-gray-900"
        )}
      >
        {value}
      </p>
    </div>
  );
}

function ScoreBadge({ score, passed }: { score: number; passed: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold",
        passed ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          passed ? "bg-green-500" : "bg-red-500"
        )}
      />
      {(score * 100).toFixed(0)}%
    </span>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function ValidationPage() {
  const { user, isLoading: authLoading } = useAuth();
  const queryClient = useQueryClient();
  const [runError, setRunError] = useState<string | null>(null);

  const isAdmin =
    user?.roles.some((r) => r.role_type === SYSTEM_ADMIN_ROLE_TYPE) ?? false;

  const { data: summary } = useQuery<ValidationSummary | null>({
    queryKey: ["validation-summary"],
    queryFn: fetchSummary,
    enabled: isAdmin,
    retry: false,
  });

  const { data: runs = [], isLoading: runsLoading } = useQuery<ValidationRun[]>(
    {
      queryKey: ["validation-runs"],
      queryFn: fetchRuns,
      enabled: isAdmin,
    }
  );

  const { data: gold = [] } = useQuery<GoldQuestion[]>({
    queryKey: ["validation-gold"],
    queryFn: fetchGold,
    enabled: isAdmin,
  });

  // Build a lookup map: question_id → GoldQuestion
  const goldMap = Object.fromEntries(gold.map((q) => [q.question_id, q]));

  // Latest batch = runs sharing the same run_at second as the first (newest) run
  const latestBatch = (() => {
    if (!runs.length) return [];
    const latestSecond = runs[0].run_at.slice(0, 19);
    return runs.filter((r) => r.run_at.slice(0, 19) === latestSecond);
  })();

  const mutation = useMutation({
    mutationFn: triggerRun,
    onSuccess: () => {
      setRunError(null);
      queryClient.invalidateQueries({ queryKey: ["validation-runs"] });
      queryClient.invalidateQueries({ queryKey: ["validation-summary"] });
    },
    onError: (err) => {
      setRunError(err instanceof Error ? err.message : "Run failed");
    },
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
      {/* ── Header ──────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-gray-900">
            Validation
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            Run the QA harness against gold-standard questions and review
            results.
          </p>
        </div>

        <button
          type="button"
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          className={cn(
            "flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors",
            "bg-blue-600 text-white hover:bg-blue-700",
            "disabled:cursor-not-allowed disabled:opacity-60"
          )}
        >
          {mutation.isPending ? (
            <>
              <svg
                className="h-4 w-4 animate-spin"
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <circle
                  className="opacity-25"
                  cx="12"
                  cy="12"
                  r="10"
                  stroke="currentColor"
                  strokeWidth="4"
                />
                <path
                  className="opacity-75"
                  fill="currentColor"
                  d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                />
              </svg>
              Running…
            </>
          ) : (
            "Run Validation"
          )}
        </button>
      </div>

      {/* ── In-progress notice ──────────────────────────────────── */}
      {mutation.isPending && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
          Validation in progress — each question is sent through Ollama. This
          takes <strong>30–120 seconds</strong>. Please wait.
        </div>
      )}

      {/* ── Error banner ────────────────────────────────────────── */}
      {runError && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {runError}
        </div>
      )}

      {/* ── Summary stats ───────────────────────────────────────── */}
      {summary ? (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
          <StatCard label="Total" value={String(summary.total)} />
          <StatCard
            label="Passed"
            value={String(summary.passed)}
            highlight="green"
          />
          <StatCard
            label="Failed"
            value={String(summary.failed)}
            highlight={summary.failed > 0 ? "red" : undefined}
          />
          <StatCard
            label="Pass Rate"
            value={`${(summary.pass_rate * 100).toFixed(0)}%`}
            highlight={summary.pass_rate >= 0.7 ? "green" : "red"}
          />
          <StatCard
            label="Avg Score"
            value={`${(summary.avg_score * 100).toFixed(0)}%`}
          />
        </div>
      ) : (
        !runsLoading && (
          <div className="rounded-xl border border-dashed border-gray-300 bg-white px-6 py-10 text-center">
            <p className="text-sm text-gray-500">
              No validation runs yet. Click{" "}
              <strong>Run Validation</strong> to start.
            </p>
          </div>
        )
      )}

      {/* ── Latest batch results table ──────────────────────────── */}
      {latestBatch.length > 0 && (
        <section>
          <h2 className="mb-3 text-base font-medium text-gray-700">
            Latest run —{" "}
            {new Date(latestBatch[0].run_at).toLocaleString(undefined, {
              month: "short",
              day: "numeric",
              hour: "2-digit",
              minute: "2-digit",
            })}
          </h2>

          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="px-4 py-3">Question</th>
                  <th className="px-4 py-3">Domain</th>
                  <th className="px-4 py-3">AI Answer</th>
                  <th className="px-4 py-3 whitespace-nowrap">Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {latestBatch.map((run) => {
                  const q = goldMap[run.question_id];
                  return (
                    <tr
                      key={run.run_id}
                      className="transition-colors hover:bg-gray-50"
                    >
                      <td className="px-4 py-3 font-medium text-gray-900 max-w-xs">
                        {q?.question_text ?? (
                          <span className="italic text-gray-400">
                            Unknown question
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                        {q?.domain ?? "—"}
                      </td>
                      <td className="px-4 py-3 text-gray-600 max-w-xs">
                        <span className="line-clamp-2">{run.ai_answer}</span>
                      </td>
                      <td className="px-4 py-3">
                        <ScoreBadge
                          score={run.similarity_score}
                          passed={run.passed}
                        />
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {/* ── Gold standards reference ─────────────────────────────── */}
      {gold.length > 0 && (
        <section>
          <h2 className="mb-3 text-base font-medium text-gray-700">
            Gold Standards ({gold.length})
          </h2>

          <div className="overflow-hidden rounded-xl border border-gray-200 bg-white">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 bg-gray-50 text-left text-xs font-semibold uppercase tracking-wide text-gray-500">
                  <th className="px-4 py-3">Question</th>
                  <th className="px-4 py-3">Domain</th>
                  <th className="px-4 py-3">Expected Answer</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {gold.map((q) => (
                  <tr
                    key={q.question_id}
                    className="transition-colors hover:bg-gray-50"
                  >
                    <td className="px-4 py-3 font-medium text-gray-900 max-w-xs">
                      {q.question_text}
                    </td>
                    <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                      {q.domain ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-600 max-w-xs">
                      <span className="line-clamp-3">{q.gold_answer}</span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
