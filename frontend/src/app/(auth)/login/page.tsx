/**
 * Login page — email + password form.
 *
 * useSearchParams() must be wrapped in Suspense (Next.js App Router requirement).
 * We split the actual form into <LoginForm> (a client component) and wrap it
 * here in a <Suspense> boundary.
 */

import { Suspense } from "react";
import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 px-4">
      <Suspense
        fallback={
          <div className="w-full max-w-md rounded-xl border bg-white p-8 shadow-sm">
            <p className="text-sm text-gray-400">Loading…</p>
          </div>
        }
      >
        <LoginForm />
      </Suspense>
    </div>
  );
}
