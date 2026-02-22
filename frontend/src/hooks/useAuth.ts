/**
 * useAuth — Returns the currently authenticated user and a logout function.
 *
 * The JWT is stored in an httpOnly cookie (not readable from JS), so we fetch
 * the current user from the `/auth/me` endpoint (proxied via /api/backend).
 *
 * Usage:
 *   const { user, logout } = useAuth();
 */

"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useCallback } from "react";

export interface AuthUser {
  user_id: string;
  email: string;
  default_format: string;
  is_active: boolean;
  created_at: string;
  roles: Array<{
    role_id: string;
    role_name: string;
    role_type: string;
    domain: string | null;
  }>;
}

async function fetchCurrentUser(): Promise<AuthUser> {
  const res = await fetch("/api/backend/auth/me", {
    credentials: "include",
  });

  if (!res.ok) {
    throw new Error("Not authenticated");
  }

  return res.json();
}

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data: user, isLoading } = useQuery<AuthUser>({
    queryKey: ["auth", "me"],
    queryFn: fetchCurrentUser,
    // Don't retry on 401 — the user is simply not authenticated
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  const logout = useCallback(async () => {
    try {
      await fetch("/api/auth", { method: "DELETE" });
    } finally {
      // Clear the cached user regardless of whether the DELETE succeeded
      queryClient.clear();
      router.push("/login");
    }
  }, [queryClient, router]);

  return { user: user ?? null, isLoading, logout };
}
