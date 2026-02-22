"use client";

/**
 * ArchiveToggle — Checkbox to include archived documents in the query.
 */

interface ArchiveToggleProps {
  value: boolean;
  onChange: (value: boolean) => void;
}

export default function ArchiveToggle({ value, onChange }: ArchiveToggleProps) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-600 select-none">
      <input
        type="checkbox"
        checked={value}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-gray-300 accent-blue-600"
      />
      Include archived documents
    </label>
  );
}
