"use client";

/**
 * Admin — Users page.
 *
 * Accessible only to System Admin role users.
 * Renders:
 *   - UserTable: list of all users with their roles
 *   - CreateUserForm: create new user accounts
 *   - RoleAssignmentPanel: assign/remove roles per user
 */

import { useAuth } from "@/hooks/useAuth";
import UserTable from "@/components/admin/UserTable";
import CreateUserForm from "@/components/admin/CreateUserForm";
import RoleAssignmentPanel from "@/components/admin/RoleAssignmentPanel";

const SYSTEM_ADMIN_ROLE_TYPE = "SYSTEM_ADMIN";

export default function AdminUsersPage() {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-sm text-gray-500">
        Loading…
      </div>
    );
  }

  const isAdmin = user?.roles.some(
    (r) => r.role_type === SYSTEM_ADMIN_ROLE_TYPE
  );

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
    <div className="mx-auto max-w-7xl space-y-8">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight text-gray-900">
          User management
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Create accounts and manage role assignments.
        </p>
      </div>

      {/* User list */}
      <section>
        <h2 className="mb-3 text-base font-medium text-gray-700">
          All users
        </h2>
        <UserTable />
      </section>

      {/* Create & role assignment — side by side on wider screens */}
      <div className="grid gap-6 lg:grid-cols-2">
        <CreateUserForm />
        <RoleAssignmentPanel />
      </div>
    </div>
  );
}
