"use client";

/**
 * Navbar — top navigation bar placeholder.
 *
 * Full implementation (links, user menu, role-aware items) is added in
 * TASK-12 and TASK-13. This version provides the layout shell and a
 * working logout button.
 */

import { useAuth } from "@/hooks/useAuth";

export default function Navbar() {
  const { user, logout } = useAuth();

  return (
    <header className="flex h-14 items-center justify-between border-b bg-white px-6 shadow-sm">
      <span className="text-lg font-semibold tracking-tight text-gray-900">
        Policy System
      </span>

      <nav className="flex items-center gap-4">
        {user && (
          <>
            <span className="text-sm text-gray-600">{user.email}</span>
            <button
              onClick={logout}
              className="rounded-md border border-gray-300 px-3 py-1 text-sm text-gray-700 transition-colors hover:bg-gray-100"
            >
              Sign out
            </button>
          </>
        )}
      </nav>
    </header>
  );
}
