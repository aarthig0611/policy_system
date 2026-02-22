"use client";

/**
 * RoleAssignmentPanel — assign or remove roles from a selected user.
 *
 * - User dropdown: populated from ["admin", "users"] query cache.
 * - Role list: fetched from GET /api/backend/admin/roles
 * - Assign: POST /api/backend/admin/users/{user_id}/roles  (body: { role_id })
 * - Remove: DELETE /api/backend/admin/users/{user_id}/roles/{role_id}
 * Both mutations invalidate ["admin", "users"].
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { RoleResponse, UserResponse } from "@/types/admin";

async function fetchUsers(): Promise<UserResponse[]> {
  const res = await fetch("/api/backend/admin/users", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch users");
  return res.json();
}

async function fetchRoles(): Promise<RoleResponse[]> {
  const res = await fetch("/api/backend/admin/roles", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch roles");
  return res.json();
}

async function assignRole(userId: string, roleId: string): Promise<void> {
  const res = await fetch(`/api/backend/admin/users/${userId}/roles`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ role_id: roleId }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to assign role");
  }
}

async function removeRole(userId: string, roleId: string): Promise<void> {
  const res = await fetch(
    `/api/backend/admin/users/${userId}/roles/${roleId}`,
    {
      method: "DELETE",
      credentials: "include",
    }
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to remove role");
  }
}

function RoleBadge({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20">
      {name}
    </span>
  );
}

export default function RoleAssignmentPanel() {
  const queryClient = useQueryClient();
  const [selectedUserId, setSelectedUserId] = useState<string>("");
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  const { data: users, isLoading: usersLoading } = useQuery<UserResponse[]>({
    queryKey: ["admin", "users"],
    queryFn: fetchUsers,
  });

  const { data: roles, isLoading: rolesLoading } = useQuery<RoleResponse[]>({
    queryKey: ["admin", "roles"],
    queryFn: fetchRoles,
  });

  const selectedUser = users?.find((u) => u.user_id === selectedUserId) ?? null;
  const assignedRoleIds = new Set(selectedUser?.roles.map((r) => r.role_id) ?? []);

  function showSuccess(msg: string) {
    setActionError(null);
    setActionSuccess(msg);
    setTimeout(() => setActionSuccess(null), 4000);
  }

  function showError(msg: string) {
    setActionSuccess(null);
    setActionError(msg);
    setTimeout(() => setActionError(null), 6000);
  }

  const assignMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      assignRole(userId, roleId),
    onSuccess: (_, { roleId }) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      const roleName = roles?.find((r) => r.role_id === roleId)?.role_name ?? roleId;
      showSuccess(`Role "${roleName}" assigned successfully.`);
    },
    onError: (err) => {
      showError(err instanceof Error ? err.message : "Failed to assign role.");
    },
  });

  const removeMutation = useMutation({
    mutationFn: ({ userId, roleId }: { userId: string; roleId: string }) =>
      removeRole(userId, roleId),
    onSuccess: (_, { roleId }) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      const roleName = roles?.find((r) => r.role_id === roleId)?.role_name ?? roleId;
      showSuccess(`Role "${roleName}" removed successfully.`);
    },
    onError: (err) => {
      showError(err instanceof Error ? err.message : "Failed to remove role.");
    },
  });

  const isPending = assignMutation.isPending || removeMutation.isPending;

  const selectBase = cn(
    "block w-full rounded-md border px-3 py-2 text-sm",
    "outline-none transition-colors",
    "focus:border-blue-500 focus:ring-2 focus:ring-blue-200",
    "disabled:cursor-not-allowed disabled:opacity-50"
  );

  return (
    <div className="rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-base font-semibold text-gray-900">
        Role Assignment
      </h2>

      {/* User selector */}
      <div className="mb-4">
        <label
          htmlFor="ra-user"
          className="block text-sm font-medium text-gray-700"
        >
          Select user
        </label>
        <select
          id="ra-user"
          value={selectedUserId}
          onChange={(e) => {
            setSelectedUserId(e.target.value);
            setActionError(null);
            setActionSuccess(null);
          }}
          className={selectBase}
          disabled={usersLoading || isPending}
        >
          <option value="">— Choose a user —</option>
          {(users ?? []).map((u) => (
            <option key={u.user_id} value={u.user_id}>
              {u.email}
            </option>
          ))}
        </select>
      </div>

      {/* Feedback banners */}
      {actionError && (
        <div className="mb-3 rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
          {actionError}
        </div>
      )}
      {actionSuccess && (
        <div className="mb-3 rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
          {actionSuccess}
        </div>
      )}

      {/* Role list — only shown when a user is selected */}
      {selectedUser && (
        <div>
          <p className="mb-2 text-sm text-gray-600">
            Current roles for <strong>{selectedUser.email}</strong>:
          </p>
          <div className="mb-4 flex flex-wrap gap-1">
            {selectedUser.roles.length === 0 ? (
              <span className="text-xs text-gray-400">No roles assigned</span>
            ) : (
              selectedUser.roles.map((r) => (
                <RoleBadge key={r.role_id} name={r.role_name} />
              ))
            )}
          </div>

          {rolesLoading ? (
            <p className="text-sm text-gray-400">Loading roles…</p>
          ) : (
            <div className="divide-y divide-gray-100 rounded-md border">
              {(roles ?? []).map((role) => {
                const assigned = assignedRoleIds.has(role.role_id);
                return (
                  <div
                    key={role.role_id}
                    className="flex items-center justify-between px-4 py-3"
                  >
                    <div>
                      <p className="text-sm font-medium text-gray-900">
                        {role.role_name}
                      </p>
                      <p className="text-xs text-gray-500">
                        {role.role_type}
                        {role.domain ? ` · ${role.domain}` : ""}
                      </p>
                    </div>
                    {assigned ? (
                      <button
                        onClick={() =>
                          removeMutation.mutate({
                            userId: selectedUser.user_id,
                            roleId: role.role_id,
                          })
                        }
                        disabled={isPending}
                        className={cn(
                          "rounded-md bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700",
                          "border border-red-200 transition-colors hover:bg-red-100",
                          "disabled:cursor-not-allowed disabled:opacity-50"
                        )}
                      >
                        Remove
                      </button>
                    ) : (
                      <button
                        onClick={() =>
                          assignMutation.mutate({
                            userId: selectedUser.user_id,
                            roleId: role.role_id,
                          })
                        }
                        disabled={isPending}
                        className={cn(
                          "rounded-md bg-blue-50 px-3 py-1.5 text-xs font-medium text-blue-700",
                          "border border-blue-200 transition-colors hover:bg-blue-100",
                          "disabled:cursor-not-allowed disabled:opacity-50"
                        )}
                      >
                        Assign
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
