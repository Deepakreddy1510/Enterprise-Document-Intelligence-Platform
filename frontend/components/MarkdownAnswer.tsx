"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import type { Source } from "../types";

export function linkifyCitations(content: string, sources: Source[]): string {
  const allowed = new Set(sources.map((source) => source.citation_id));
  return content.replace(/\[(S\d+)\]/g, (marker, citationId: string) =>
    allowed.has(citationId) ? `[${citationId}](citation:${citationId})` : marker,
  );
}

export function MarkdownAnswer({
  content,
  sources,
  onCitation,
}: {
  content: string;
  sources: Source[];
  onCitation: (source: Source) => void;
}) {
  const markdown = linkifyCitations(content, sources);
  return (
    <div className="markdown-answer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => {
            const citationId = href?.startsWith("citation:") ? href.slice("citation:".length) : null;
            const source = citationId ? sources.find((item) => item.citation_id === citationId) : undefined;
            if (source) {
              return <button className="citation" onClick={() => onCitation(source)} aria-label={`Open source ${source.citation_id}`}>{children}</button>;
            }
            return <a href={href}>{children}</a>;
          },
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}
