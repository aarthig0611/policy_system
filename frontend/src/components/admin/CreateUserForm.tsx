"use client";

/**
 * CreateUserForm — form for creating new user accounts.
 *
 * Fields: email (required), password (required, min 8 chars), full_name (optional, display only)
 * Submits to POST /api/backend/admin/users
 * Invalidates ["admin", "users"] query on success.
 */

import { useState, FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { UserCreatePayload, UserResponse } from "@/types/admin";

async function createUser(payload: UserCreatePayload): Promise<UserResponse> {
  const res = await fetch("/api/backend/admin/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to create user");
  }
  return res.json();
}

interface FieldError {
  email?: string;
  password?: string;
}

function validate(email: string, password: string): FieldError {
  const errors: FieldError = {};
  if (!email.trim()) {
    errors.email = "Email is required.";
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) {
    errors.email = "Please enter a valid email address.";
  }
  if (!password) {
    errors.password = "Password is required.";
  } else if (password.length < 8) {
    errors.password = "Password must be at least 8 characters.";
  }
  return errors;
}

export default function CreateUserForm() {
  const queryClient = useQueryClient();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldError>({});
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createUser,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
      setEmail("");
      setPassword("");
      setFieldErrors({});
      setSuccessMsg(`User ${data.email} created successfully.`);
      // Clear success message after 5 seconds
      setTimeout(() => setSuccessMsg(null), 5000);
    },
  });

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSuccessMsg(null);

    const errors = validate(email, password);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});

    mutation.mutate({ email: email.trim(), password });
  }

  const inputBase = cn(
    "mt-1 block w-full rounded-md border px-3 py-2 text-sm",
    "outline-none transition-colors",
    "focus:border-blue-500 focus:ring-2 focus:ring-blue-200",
    "disabled:cursor-not-allowed disabled:opacity-50"
  );

  return (
    <div className="rounded-lg border bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-base font-semibold text-gray-900">
        Create New User
      </h2>

      <form onSubmit={handleSubmit} noValidate className="space-y-4">
        {/* Email */}
        <div>
          <label
            htmlFor="cu-email"
            className="block text-sm font-medium text-gray-700"
          >
            Email address <span className="text-red-500">*</span>
          </label>
          <input
            id="cu-email"
            type="email"
            autoComplete="off"
            value={email}
            onChange={(e) => {
              setEmail(e.target.value);
              if (fieldErrors.email) setFieldErrors((p) => ({ ...p, email: undefined }));
            }}
            className={cn(inputBase, fieldErrors.email && "border-red-400")}
            disabled={mutation.isPending}
            placeholder="user@example.com"
          />
          {fieldErrors.email && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.email}</p>
          )}
        </div>

        {/* Password */}
        <div>
          <label
            htmlFor="cu-password"
            className="block text-sm font-medium text-gray-700"
          >
            Password <span className="text-red-500">*</span>
          </label>
          <input
            id="cu-password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value);
              if (fieldErrors.password) setFieldErrors((p) => ({ ...p, password: undefined }));
            }}
            className={cn(inputBase, fieldErrors.password && "border-red-400")}
            disabled={mutation.isPending}
            placeholder="Min. 8 characters"
          />
          {fieldErrors.password && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.password}</p>
          )}
        </div>

        {/* Mutation error */}
        {mutation.isError && (
          <p className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">
            {mutation.error instanceof Error
              ? mutation.error.message
              : "An unexpected error occurred."}
          </p>
        )}

        {/* Success message */}
        {successMsg && (
          <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
            {successMsg}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending}
          className={cn(
            "rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white",
            "transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300",
            "disabled:cursor-not-allowed disabled:opacity-50"
          )}
        >
          {mutation.isPending ? "Creating…" : "Create user"}
        </button>
      </form>
    </div>
  );
}
