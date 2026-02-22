"use client";

/**
 * DomainSelector — Dropdown to restrict a query to a single domain.
 *
 * Only rendered when the user has multiple roles/domains.
 * "All domains" is represented as null.
 */

interface DomainSelectorProps {
  domains: string[];
  value: string | null;
  onChange: (value: string | null) => void;
}

export default function DomainSelector({
  domains,
  value,
  onChange,
}: DomainSelectorProps) {
  if (domains.length <= 1) {
    return null;
  }

  function handleChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const selected = e.target.value;
    onChange(selected === "" ? null : selected);
  }

  return (
    <div className="flex items-center gap-2">
      <label htmlFor="domain-select" className="text-sm text-gray-600 whitespace-nowrap">
        Domain:
      </label>
      <select
        id="domain-select"
        value={value ?? ""}
        onChange={handleChange}
        className="rounded-md border border-gray-200 bg-white px-2 py-1 text-sm text-gray-700 outline-none focus:border-blue-400 focus:ring-1 focus:ring-blue-200"
      >
        <option value="">All domains</option>
        {domains.map((domain) => (
          <option key={domain} value={domain}>
            {domain}
          </option>
        ))}
      </select>
    </div>
  );
}
