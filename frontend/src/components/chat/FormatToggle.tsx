"use client";

/**
 * FormatToggle — Toggle between "Executive Summary" and "Detailed" response formats.
 *
 * Session-level state lives in the parent chat page.
 */

import { cn } from "@/lib/utils";

export type ResponseFormat = "summary" | "detailed";

interface FormatToggleProps {
  value: ResponseFormat;
  onChange: (value: ResponseFormat) => void;
}

export default function FormatToggle({ value, onChange }: FormatToggleProps) {
  return (
    <div className="inline-flex items-center rounded-md border border-gray-200 bg-gray-50 p-0.5 text-sm">
      <button
        type="button"
        onClick={() => onChange("summary")}
        className={cn(
          "rounded px-3 py-1 font-medium transition-colors",
          value === "summary"
            ? "bg-white text-gray-900 shadow-sm"
            : "text-gray-500 hover:text-gray-700"
        )}
        aria-pressed={value === "summary"}
      >
        Executive Summary
      </button>
      <button
        type="button"
        onClick={() => onChange("detailed")}
        className={cn(
          "rounded px-3 py-1 font-medium transition-colors",
          value === "detailed"
            ? "bg-white text-gray-900 shadow-sm"
            : "text-gray-500 hover:text-gray-700"
        )}
        aria-pressed={value === "detailed"}
      >
        Detailed
      </button>
    </div>
  );
}
