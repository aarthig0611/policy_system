"use client";

/**
 * Profile page — lets the authenticated user view their profile and set their
 * default response format preference.
 *
 * Fetches the current user via GET /api/backend/auth/me (same endpoint as
 * useAuth, re-used through the shared query key ["auth", "me"]).
 *
 * Updates default_format via PATCH /api/backend/auth/me.
 * Available to any authenticated user — no admin role required.
 */

import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { AuthUser } from "@/hooks/useAuth";
import type { components } from "@/types/api";

type ResponseFormat = components["schemas"]["ResponseFormat"];

// Re-use the same fetch function shape as useAuth to share the cache entry
async function fetchCurrentUser(): Promise<AuthUser> {
  const res = await fetch("/api/backend/auth/me", {
    credentials: "include",
  });
  if (!res.ok) {
    throw new Error("Not authenticated");
  }
  return res.json();
}

async function updateDefaultFormat(
  default_format: ResponseFormat
): Promise<AuthUser> {
  const res = await fetch("/api/backend/auth/me", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ default_format }),
  });
  if (!res.ok) {
    const body = await res
      .json()
      .catch(() => ({ detail: "Failed to update profile" }));
    throw new Error(body.detail ?? "Failed to update profile");
  }
  return res.json();
}

const FORMAT_OPTIONS: { value: ResponseFormat; label: string; description: string }[] =
  [
    {
      value: "EXECUTIVE_SUMMARY",
      label: "Executive Summary",
      description:
        "Concise answers without citations — best for quick lookups.",
    },
    {
      value: "DETAILED_RESPONSE",
      label: "Detailed",
      description:
        "Full responses with source citations — best for in-depth research.",
    },
  ];

export default function ProfilePage() {
  const queryClient = useQueryClient();

  const { data: user, isLoading } = useQuery<AuthUser>({
    queryKey: ["auth", "me"],
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  // Local state mirrors the user's current default_format
  const [selectedFormat, setSelectedFormat] =
    useState<ResponseFormat>("EXECUTIVE_SUMMARY");

  // Sync local state when user data loads
  useEffect(() => {
    if (user?.default_format) {
      setSelectedFormat(user.default_format as ResponseFormat);
    }
  }, [user?.default_format]);

  const [savedBanner, setSavedBanner] = useState(false);

  const mutation = useMutation<AuthUser, Error, ResponseFormat>({
    mutationFn: updateDefaultFormat,
    onSuccess: (updatedUser) => {
      // Update both the profile query and the auth cache
      queryClient.setQueryData(["auth", "me"], updatedUser);
      setSavedBanner(true);
      setTimeout(() => setSavedBanner(false), 3000);
    },
  });

  function handleSave() {
    if (!user) return;
    // Only call the API if the value actually changed
    if (selectedFormat === (user.default_format as ResponseFormat)) {
      setSavedBanner(true);
      setTimeout(() => setSavedBanner(false), 3000);
      return;
    }
    mutation.mutate(selectedFormat);
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-gray-500">Loading profile…</p>
      </div>
    );
  }

  if (!user) {
    return (
      <div className="flex items-center justify-center py-20">
        <p className="text-sm text-red-600">Unable to load profile.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-xl font-semibold text-gray-900">Profile</h1>

      {/* User info */}
      <div className="rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="mb-3 text-sm font-medium text-gray-700">
          Account details
        </h2>
        <dl className="space-y-2 text-sm">
          <div className="flex justify-between">
            <dt className="text-gray-500">Email</dt>
            <dd className="font-medium text-gray-900">{user.email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Status</dt>
            <dd>
              <span
                className={cn(
                  "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium",
                  user.is_active
                    ? "bg-green-50 text-green-700 ring-1 ring-inset ring-green-600/20"
                    : "bg-red-50 text-red-700 ring-1 ring-inset ring-red-600/20"
                )}
              >
                {user.is_active ? "Active" : "Inactive"}
              </span>
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-gray-500">Roles</dt>
            <dd className="text-right font-medium text-gray-900">
              {user.roles.length === 0
                ? "None assigned"
                : user.roles.map((r) => r.role_name).join(", ")}
            </dd>
          </div>
        </dl>
      </div>

      {/* Default format selector */}
      <div className="rounded-lg border bg-white p-5 shadow-sm">
        <h2 className="mb-1 text-sm font-medium text-gray-700">
          Default response format
        </h2>
        <p className="mb-4 text-xs text-gray-400">
          This sets the format used when you submit a query without an explicit
          override.
        </p>

        <fieldset className="space-y-3">
          <legend className="sr-only">Response format</legend>
          {FORMAT_OPTIONS.map((opt) => {
            const checked = selectedFormat === opt.value;
            return (
              <label
                key={opt.value}
                className={cn(
                  "flex cursor-pointer items-start gap-3 rounded-lg border p-4 transition-colors",
                  checked
                    ? "border-blue-500 bg-blue-50"
                    : "border-gray-200 hover:border-gray-300 hover:bg-gray-50",
                  mutation.isPending && "cursor-not-allowed opacity-60"
                )}
              >
                <input
                  type="radio"
                  name="default_format"
                  value={opt.value}
                  checked={checked}
                  onChange={() => setSelectedFormat(opt.value)}
                  disabled={mutation.isPending}
                  className="mt-0.5 h-4 w-4 text-blue-600 accent-blue-600"
                />
                <span>
                  <span
                    className={cn(
                      "block text-sm font-medium",
                      checked ? "text-blue-900" : "text-gray-900"
                    )}
                  >
                    {opt.label}
                  </span>
                  <span className="block text-xs text-gray-500">
                    {opt.description}
                  </span>
                </span>
              </label>
            );
          })}
        </fieldset>

        {/* Error banner */}
        {mutation.isError && (
          <p className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {mutation.error instanceof Error
              ? mutation.error.message
              : "An unexpected error occurred."}
          </p>
        )}

        {/* Success banner */}
        {savedBanner && (
          <p className="mt-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
            Preference saved.
          </p>
        )}

        <button
          type="button"
          onClick={handleSave}
          disabled={mutation.isPending}
          className={cn(
            "mt-4 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white",
            "transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300",
            "disabled:cursor-not-allowed disabled:opacity-50"
          )}
        >
          {mutation.isPending ? "Saving…" : "Save preference"}
        </button>
      </div>
    </div>
  );
}
