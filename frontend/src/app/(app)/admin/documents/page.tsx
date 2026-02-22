"use client";

/**
 * Admin — Documents page.
 *
 * Accessible only to System Admin role users.
 * Renders:
 *   - DocumentUploadForm: register a new document with mandatory role tagging
 *   - DocumentTable: list all documents with archive toggle per row
 */

import { useAuth } from "@/hooks/useAuth";
import DocumentUploadForm from "@/components/admin/DocumentUploadForm";
import DocumentTable from "@/components/admin/DocumentTable";

const SYSTEM_ADMIN_ROLE_TYPE = "SYSTEM_ADMIN";

export default function AdminDocumentsPage() {
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
          Document management
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Register new policy documents and manage access control.
        </p>
      </div>

      {/* Upload form */}
      <section className="max-w-xl">
        <DocumentUploadForm />
      </section>

      {/* Document list */}
      <section>
        <h2 className="mb-3 text-base font-medium text-gray-700">
          All documents
        </h2>
        <DocumentTable />
      </section>
    </div>
  );
}
