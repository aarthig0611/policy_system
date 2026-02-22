"use client";

/**
 * DocumentUploadForm — upload a document and assign access roles.
 *
 * File input: .pdf, .docx, .txt, .md
 * Role tagging: multi-select (mandatory — at least one role required)
 * Title: required text field
 *
 * Submission note: The backend's POST /admin/documents endpoint accepts a JSON
 * body with { title, storage_uri, role_ids }. This form uses the selected
 * file's name as the storage_uri. A future ingestion endpoint upgrade may
 * accept multipart/form-data with a file binary.
 *
 * Invalidates ["admin", "documents"] on success.
 */

import { useState, useRef, FormEvent, ChangeEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { DocumentCreatePayload, DocumentResponse, RoleResponse } from "@/types/admin";

async function fetchRoles(): Promise<RoleResponse[]> {
  const res = await fetch("/api/backend/admin/roles", {
    credentials: "include",
  });
  if (!res.ok) throw new Error("Failed to fetch roles");
  return res.json();
}

async function uploadDocument(
  payload: DocumentCreatePayload
): Promise<DocumentResponse> {
  const res = await fetch("/api/backend/admin/documents", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to register document");
  }
  return res.json();
}

const ACCEPTED_TYPES = [".pdf", ".docx", ".txt", ".md"];

interface FormErrors {
  title?: string;
  file?: string;
  roles?: string;
}

function validate(
  title: string,
  file: File | null,
  selectedRoleIds: string[]
): FormErrors {
  const errors: FormErrors = {};
  if (!title.trim()) errors.title = "Title is required.";
  if (!file) errors.file = "Please select a file to upload.";
  if (selectedRoleIds.length === 0)
    errors.roles = "At least one role must be selected.";
  return errors;
}

export default function DocumentUploadForm() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [title, setTitle] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [selectedRoleIds, setSelectedRoleIds] = useState<string[]>([]);
  const [fieldErrors, setFieldErrors] = useState<FormErrors>({});
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const { data: roles, isLoading: rolesLoading } = useQuery<RoleResponse[]>({
    queryKey: ["admin", "roles"],
    queryFn: fetchRoles,
  });

  const mutation = useMutation({
    mutationFn: uploadDocument,
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["admin", "documents"] });
      // Reset form
      setTitle("");
      setFile(null);
      setSelectedRoleIds([]);
      setFieldErrors({});
      if (fileInputRef.current) fileInputRef.current.value = "";
      setSuccessMsg(`Document "${data.title}" registered successfully.`);
      setTimeout(() => setSuccessMsg(null), 5000);
    },
  });

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    const selected = e.target.files?.[0] ?? null;
    setFile(selected);
    if (fieldErrors.file) setFieldErrors((p) => ({ ...p, file: undefined }));
    // Auto-fill title from filename if title is empty
    if (selected && !title.trim()) {
      const nameWithoutExt = selected.name.replace(/\.[^.]+$/, "");
      setTitle(nameWithoutExt);
    }
  }

  function toggleRole(roleId: string) {
    setSelectedRoleIds((prev) => {
      const next = prev.includes(roleId)
        ? prev.filter((id) => id !== roleId)
        : [...prev, roleId];
      if (fieldErrors.roles && next.length > 0) {
        setFieldErrors((p) => ({ ...p, roles: undefined }));
      }
      return next;
    });
  }

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setSuccessMsg(null);

    const errors = validate(title, file, selectedRoleIds);
    if (Object.keys(errors).length > 0) {
      setFieldErrors(errors);
      return;
    }
    setFieldErrors({});

    // Use the file name as storage_uri — the backend ingestion pipeline
    // will resolve this to the actual stored path.
    mutation.mutate({
      title: title.trim(),
      storage_uri: file!.name,
      role_ids: selectedRoleIds,
    });
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
        Upload Document
      </h2>

      <form onSubmit={handleSubmit} noValidate className="space-y-5">
        {/* File input */}
        <div>
          <label
            htmlFor="du-file"
            className="block text-sm font-medium text-gray-700"
          >
            File <span className="text-red-500">*</span>
          </label>
          <input
            id="du-file"
            type="file"
            ref={fileInputRef}
            accept={ACCEPTED_TYPES.join(",")}
            onChange={handleFileChange}
            disabled={mutation.isPending}
            className={cn(
              "mt-1 block w-full text-sm text-gray-700",
              "file:mr-4 file:rounded-md file:border-0 file:bg-blue-50",
              "file:px-4 file:py-2 file:text-sm file:font-medium file:text-blue-700",
              "file:transition-colors file:hover:bg-blue-100",
              "disabled:cursor-not-allowed disabled:opacity-50",
              fieldErrors.file && "rounded-md border border-red-400"
            )}
          />
          <p className="mt-1 text-xs text-gray-400">
            Accepted: {ACCEPTED_TYPES.join(", ")}
          </p>
          {fieldErrors.file && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.file}</p>
          )}
        </div>

        {/* Title */}
        <div>
          <label
            htmlFor="du-title"
            className="block text-sm font-medium text-gray-700"
          >
            Title <span className="text-red-500">*</span>
          </label>
          <input
            id="du-title"
            type="text"
            value={title}
            onChange={(e) => {
              setTitle(e.target.value);
              if (fieldErrors.title) setFieldErrors((p) => ({ ...p, title: undefined }));
            }}
            disabled={mutation.isPending}
            placeholder="Enter document title"
            className={cn(inputBase, fieldErrors.title && "border-red-400")}
          />
          {fieldErrors.title && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.title}</p>
          )}
        </div>

        {/* Role multi-select */}
        <div>
          <p className="block text-sm font-medium text-gray-700">
            Access roles <span className="text-red-500">*</span>
          </p>
          <p className="mb-2 text-xs text-gray-400">
            Select all roles that may access this document.
          </p>

          {rolesLoading ? (
            <p className="text-sm text-gray-400">Loading roles…</p>
          ) : (roles ?? []).length === 0 ? (
            <p className="text-sm text-gray-400">No roles available.</p>
          ) : (
            <div
              className={cn(
                "space-y-2 rounded-md border p-3",
                fieldErrors.roles && "border-red-400"
              )}
            >
              {(roles ?? []).map((role) => {
                const checked = selectedRoleIds.includes(role.role_id);
                return (
                  <label
                    key={role.role_id}
                    className={cn(
                      "flex cursor-pointer items-start gap-3 rounded-md px-2 py-1.5",
                      "transition-colors hover:bg-gray-50",
                      mutation.isPending && "cursor-not-allowed opacity-50"
                    )}
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => toggleRole(role.role_id)}
                      disabled={mutation.isPending}
                      className="mt-0.5 h-4 w-4 rounded border-gray-300 text-blue-600"
                    />
                    <span>
                      <span className="block text-sm font-medium text-gray-900">
                        {role.role_name}
                      </span>
                      <span className="block text-xs text-gray-500">
                        {role.role_type}
                        {role.domain ? ` · ${role.domain}` : ""}
                      </span>
                    </span>
                  </label>
                );
              })}
            </div>
          )}

          {fieldErrors.roles && (
            <p className="mt-1 text-xs text-red-600">{fieldErrors.roles}</p>
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

        {/* Success */}
        {successMsg && (
          <p className="rounded-md bg-green-50 px-3 py-2 text-sm text-green-700">
            {successMsg}
          </p>
        )}

        <button
          type="submit"
          disabled={mutation.isPending || rolesLoading}
          className={cn(
            "rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white",
            "transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-300",
            "disabled:cursor-not-allowed disabled:opacity-50"
          )}
        >
          {mutation.isPending ? "Registering…" : "Register document"}
        </button>
      </form>
    </div>
  );
}
