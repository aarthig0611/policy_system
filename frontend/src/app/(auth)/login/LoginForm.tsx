"use client";

/**
 * LoginForm — the actual client-side form component.
 *
 * Separated from page.tsx so that useSearchParams() is inside a Suspense
 * boundary as required by the Next.js App Router.
 *
 * On submit: calls POST /api/auth (route handler), which validates credentials
 * with FastAPI, sets an httpOnly cookie, and returns { ok: true }.
 * On success: redirects to /chat (or the `redirect` query param).
 * On failure: displays the error message returned by the route handler.
 */

import { useState, FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { cn } from "@/lib/utils";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get("redirect") ?? "/chat";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await fetch("/api/auth", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await res.json();

      if (!res.ok || !data.ok) {
        setError(data.error ?? "Login failed. Please try again.");
        return;
      }

      // Cookie is now set — navigate to the protected route
      router.push(redirectTo);
      router.refresh(); // clear any stale server component cache
    } catch {
      setError("Network error. Please check your connection.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="w-full max-w-md rounded-xl border bg-white p-8 shadow-sm">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight text-gray-900">
        Policy System
      </h1>
      <p className="mb-6 text-sm text-gray-500">
        Sign in to access policy documents
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-gray-700"
          >
            Email address
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={cn(
              "mt-1 block w-full rounded-md border px-3 py-2 text-sm",
              "outline-none ring-offset-0 transition-colors",
              "focus:border-blue-500 focus:ring-2 focus:ring-blue-200",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
            disabled={loading}
            placeholder="you@example.com"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-gray-700"
          >
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={cn(
              "mt-1 block w-full rounded-md border px-3 py-2 text-sm",
              "outline-none ring-offset-0 transition-colors",
              "focus:border-blue-500 focus:ring-2 focus:ring-blue-200",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
            disabled={loading}
            placeholder="••••••••"
          />
        </div>

        {error && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        <button
          type="submit"
          disabled={loading}
          className={cn(
            "w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white",
            "transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300",
            "disabled:cursor-not-allowed disabled:opacity-50"
          )}
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
