"use client";

/**
 * CitationBlock — Compact citation list rendered below assistant messages in Detailed mode.
 *
 * Only rendered when showCitations is true (Detailed format) and citations exist.
 */

import type { Citation } from "@/hooks/useChat";

interface CitationBlockProps {
  citations: Citation[];
}

function formatCitation(citation: Citation): string {
  const parts: string[] = [citation.doc_title];
  if (citation.page_number != null) {
    parts.push(`Page ${citation.page_number}`);
  }
  if (citation.para_number != null) {
    parts.push(`Para ${citation.para_number}`);
  }
  return parts.join(", ");
}

export default function CitationBlock({ citations }: CitationBlockProps) {
  if (citations.length === 0) {
    return null;
  }

  return (
    <div className="mt-2 border-t border-gray-100 pt-2">
      <p className="mb-1 text-xs font-medium uppercase tracking-wide text-gray-400">
        Sources
      </p>
      <ul className="space-y-0.5">
        {citations.map((citation, index) => (
          <li
            key={`${citation.doc_id}-${index}`}
            className="text-xs text-gray-500"
          >
            [{formatCitation(citation)}]
          </li>
        ))}
      </ul>
    </div>
  );
}
