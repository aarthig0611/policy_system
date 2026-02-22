"use client";

/**
 * CrossDomainPrompt — Modal dialog shown when the query engine returns
 * CrossDomainPermissionRequired (zero chunks matched after role filtering).
 *
 * Uses a native <dialog> element styled with Tailwind to avoid adding
 * a radix-ui Dialog dependency just for this simple modal.
 */

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface CrossDomainPromptProps {
  open: boolean;
  message: string;
  onClose: () => void;
}

export default function CrossDomainPrompt({
  open,
  message,
  onClose,
}: CrossDomainPromptProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    if (open && !dialog.open) {
      dialog.showModal();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  // Allow closing with Escape key (native dialog behaviour), but sync state
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;

    function handleClose() {
      onClose();
    }

    dialog.addEventListener("close", handleClose);
    return () => dialog.removeEventListener("close", handleClose);
  }, [onClose]);

  return (
    <dialog
      ref={dialogRef}
      className={cn(
        "rounded-xl border border-gray-200 bg-white p-0 shadow-xl",
        "backdrop:bg-black/40 backdrop:backdrop-blur-sm",
        "w-full max-w-sm"
      )}
    >
      <div className="p-6">
        <div className="mb-4 flex items-start gap-3">
          {/* Lock icon */}
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-50">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              className="text-amber-500"
              aria-hidden="true"
            >
              <rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
              <path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
          </div>
          <div>
            <h2 className="text-base font-semibold text-gray-900">
              Access Restricted
            </h2>
            <p className="mt-1 text-sm text-gray-600">{message}</p>
          </div>
        </div>

        <p className="mb-5 text-xs text-gray-500">
          Try selecting a specific domain from the domain filter, or contact your
          administrator if you believe you should have access.
        </p>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className={cn(
              "rounded-md bg-gray-900 px-4 py-2 text-sm font-medium text-white",
              "transition-colors hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400"
            )}
          >
            OK
          </button>
        </div>
      </div>
    </dialog>
  );
}
