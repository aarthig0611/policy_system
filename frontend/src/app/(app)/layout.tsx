/**
 * Protected app layout — wraps /chat, /admin/*, /profile.
 *
 * Authentication is enforced by middleware.ts before this layout renders.
 * Full sidebar / navigation is added in TASK-12 and TASK-13.
 */

import Navbar from "@/components/shared/Navbar";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-gray-50">
      <Navbar />
      <main className="flex-1 p-6">{children}</main>
    </div>
  );
}
