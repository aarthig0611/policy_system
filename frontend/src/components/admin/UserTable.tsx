"use client";

/**
 * UserTable — displays all users with their roles.
 *
 * Fetches from GET /api/backend/admin/users
 * Columns: email, is_active, created_at, roles, Actions (placeholder)
 */

import { useQuery } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { UserResponse } from "@/types/admin";

async function fetchUsers(): Promise<UserResponse[]> {
  const res = await fetch("/api/backend/admin/users", {
    credentials: "include",
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to fetch users");
  }
  return res.json();
}

function StatusBadge({ active }: { active: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        active
          ? "bg-green-100 text-green-800"
          : "bg-gray-100 text-gray-600"
      )}
    >
      {active ? "Active" : "Inactive"}
    </span>
  );
}

function RoleBadge({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20">
      {name}
    </span>
  );
}

export default function UserTable() {
  const {
    data: users,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<UserResponse[]>({
    queryKey: ["admin", "users"],
    queryFn: fetchUsers,
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-white p-8 text-center text-sm text-gray-500">
        Loading users…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">
          {error instanceof Error ? error.message : "Failed to load users"}
        </p>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm font-medium text-red-700 underline hover:text-red-900"
        >
          Retry
        </button>
      </div>
    );
  }

  const rows = users ?? [];

  return (
    <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Email
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Created
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Roles
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={5}
                className="px-6 py-8 text-center text-sm text-gray-400"
              >
                No users found.
              </td>
            </tr>
          ) : (
            rows.map((user) => (
              <tr key={user.user_id} className="hover:bg-gray-50">
                <td className="px-6 py-4 text-sm font-medium text-gray-900">
                  {user.email}
                </td>
                <td className="px-6 py-4 text-sm">
                  <StatusBadge active={user.is_active} />
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(user.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1">
                    {user.roles.length === 0 ? (
                      <span className="text-xs text-gray-400">None</span>
                    ) : (
                      user.roles.map((r) => (
                        <RoleBadge key={r.role_id} name={r.role_name} />
                      ))
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  <span className="text-xs text-gray-400">
                    {user.user_id.slice(0, 8)}…
                  </span>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
