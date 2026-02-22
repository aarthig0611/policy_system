"use client";

/**
 * DocumentTable — displays all documents with archive toggle.
 *
 * Fetches from GET /api/backend/admin/documents?include_archived=true
 * Columns: title, file_type (derived from storage_uri), is_archived, created_at, roles, Actions
 * Archive toggle: PATCH /api/backend/admin/documents/{doc_id}/archive
 * Uses optimistic update on archive toggle.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { cn } from "@/lib/utils";
import type { DocumentResponse } from "@/types/admin";

async function fetchDocuments(): Promise<DocumentResponse[]> {
  const res = await fetch(
    "/api/backend/admin/documents?include_archived=true",
    { credentials: "include" }
  );
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to fetch documents");
  }
  return res.json();
}

async function toggleArchive(
  docId: string,
  currentIsArchived: boolean
): Promise<DocumentResponse> {
  const res = await fetch(`/api/backend/admin/documents/${docId}/archive`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ is_archived: !currentIsArchived }),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? "Failed to toggle archive status");
  }
  return res.json();
}

function getFileType(storageUri: string): string {
  const ext = storageUri.split(".").pop()?.toLowerCase();
  switch (ext) {
    case "pdf":
      return "PDF";
    case "docx":
      return "DOCX";
    case "txt":
      return "TXT";
    case "md":
      return "MD";
    default:
      return ext?.toUpperCase() ?? "—";
  }
}

function ArchiveBadge({ archived }: { archived: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        archived
          ? "bg-yellow-100 text-yellow-800"
          : "bg-green-100 text-green-800"
      )}
    >
      {archived ? "Archived" : "Active"}
    </span>
  );
}

function RoleBadge({ name }: { name: string }) {
  return (
    <span className="inline-flex items-center rounded-md bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 ring-1 ring-inset ring-blue-600/20">
      {name}
    </span>
  );
}

export default function DocumentTable() {
  const queryClient = useQueryClient();

  const {
    data: documents,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<DocumentResponse[]>({
    queryKey: ["admin", "documents"],
    queryFn: fetchDocuments,
  });

  const archiveMutation = useMutation({
    mutationFn: ({
      docId,
      currentIsArchived,
    }: {
      docId: string;
      currentIsArchived: boolean;
    }) => toggleArchive(docId, currentIsArchived),

    // Optimistic update: flip the is_archived flag immediately
    onMutate: async ({ docId, currentIsArchived }) => {
      await queryClient.cancelQueries({ queryKey: ["admin", "documents"] });

      const snapshot = queryClient.getQueryData<DocumentResponse[]>([
        "admin",
        "documents",
      ]);

      queryClient.setQueryData<DocumentResponse[]>(
        ["admin", "documents"],
        (old) =>
          old?.map((doc) =>
            doc.doc_id === docId
              ? { ...doc, is_archived: !currentIsArchived }
              : doc
          ) ?? []
      );

      return { snapshot };
    },

    // Roll back on error
    onError: (_err, _vars, context) => {
      if (context?.snapshot) {
        queryClient.setQueryData(["admin", "documents"], context.snapshot);
      }
    },

    // Always refetch after settle to ensure server state
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["admin", "documents"] });
    },
  });

  if (isLoading) {
    return (
      <div className="rounded-lg border bg-white p-8 text-center text-sm text-gray-500">
        Loading documents…
      </div>
    );
  }

  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-sm text-red-700">
          {error instanceof Error ? error.message : "Failed to load documents"}
        </p>
        <button
          onClick={() => refetch()}
          className="mt-2 text-sm font-medium text-red-700 underline hover:text-red-900"
        >
          Retry
        </button>
      </div>
    );
  }

  const rows = documents ?? [];

  return (
    <div className="overflow-hidden rounded-lg border bg-white shadow-sm">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Title
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Type
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Status
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Created
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Roles
            </th>
            <th
              scope="col"
              className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500"
            >
              Actions
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100 bg-white">
          {rows.length === 0 ? (
            <tr>
              <td
                colSpan={6}
                className="px-6 py-8 text-center text-sm text-gray-400"
              >
                No documents found.
              </td>
            </tr>
          ) : (
            rows.map((doc) => (
              <tr
                key={doc.doc_id}
                className={cn(
                  "hover:bg-gray-50",
                  doc.is_archived && "opacity-60"
                )}
              >
                <td className="px-6 py-4 text-sm font-medium text-gray-900">
                  {doc.title}
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {getFileType(doc.storage_uri)}
                </td>
                <td className="px-6 py-4 text-sm">
                  <ArchiveBadge archived={doc.is_archived} />
                </td>
                <td className="px-6 py-4 text-sm text-gray-500">
                  {new Date(doc.created_at).toLocaleDateString()}
                </td>
                <td className="px-6 py-4">
                  <div className="flex flex-wrap gap-1">
                    {doc.roles.length === 0 ? (
                      <span className="text-xs text-gray-400">None</span>
                    ) : (
                      doc.roles.map((r) => (
                        <RoleBadge key={r.role_id} name={r.role_name} />
                      ))
                    )}
                  </div>
                </td>
                <td className="px-6 py-4 text-sm">
                  <button
                    onClick={() =>
                      archiveMutation.mutate({
                        docId: doc.doc_id,
                        currentIsArchived: doc.is_archived,
                      })
                    }
                    disabled={archiveMutation.isPending}
                    className={cn(
                      "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                      "border focus:outline-none focus:ring-2",
                      "disabled:cursor-not-allowed disabled:opacity-50",
                      doc.is_archived
                        ? "border-green-200 bg-green-50 text-green-700 hover:bg-green-100 focus:ring-green-200"
                        : "border-yellow-200 bg-yellow-50 text-yellow-700 hover:bg-yellow-100 focus:ring-yellow-200"
                    )}
                  >
                    {doc.is_archived ? "Unarchive" : "Archive"}
                  </button>
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );
}
