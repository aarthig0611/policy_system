"use client";

/**
 * Navbar — top navigation bar.
 *
 * Includes role-aware navigation links:
 *   - /chat — always visible when authenticated
 *   - /admin/users and /admin/documents — visible only to SYSTEM_ADMIN users
 *
 * Updated in TASK-12 to add admin navigation.
 */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const SYSTEM_ADMIN_ROLE_TYPE = "SYSTEM_ADMIN";

function NavLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const active = pathname === href || pathname.startsWith(href + "/");

  return (
    <Link
      href={href}
      className={cn(
        "rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
        active
          ? "bg-gray-100 text-gray-900"
          : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
      )}
    >
      {children}
    </Link>
  );
}

export default function Navbar() {
  const { user, logout } = useAuth();

  const isAdmin = user?.roles.some(
    (r) => r.role_type === SYSTEM_ADMIN_ROLE_TYPE
  ) ?? false;

  return (
    <header className="flex h-14 items-center justify-between border-b bg-white px-6 shadow-sm">
      <div className="flex items-center gap-6">
        <span className="text-lg font-semibold tracking-tight text-gray-900">
          Policy System
        </span>

        {user && (
          <nav className="flex items-center gap-1">
            <NavLink href="/chat">Chat</NavLink>
            {isAdmin && (
              <>
                <NavLink href="/admin/users">Users</NavLink>
                <NavLink href="/admin/documents">Documents</NavLink>
                <NavLink href="/admin/flagged">Flagged</NavLink>
              </>
            )}
            <NavLink href="/profile">Profile</NavLink>
          </nav>
        )}
      </div>

      <div className="flex items-center gap-4">
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
      </div>
    </header>
  );
}
