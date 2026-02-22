"use client";

/**
 * Client-side wrapper that supplies QueryClientProvider to the React tree.
 *
 * This must be a Client Component because QueryClientProvider uses React
 * context, which is not available in React Server Components.
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export default function QueryProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  // Create a stable QueryClient instance per browser session
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            // Don't refetch on window focus during development
            refetchOnWindowFocus: process.env.NODE_ENV === "production",
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
