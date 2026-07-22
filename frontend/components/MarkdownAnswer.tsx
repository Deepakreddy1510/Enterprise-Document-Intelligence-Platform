"use client";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Source } from "../types";

export function MarkdownAnswer({ content, sources, onCitation }: { content: string; sources: Source[]; onCitation: (source: Source) => void }) {
  const parts = content.split(/(\[S\d+\])/g);
  return <div className="markdown-answer">
    {parts.map((part, index) => {
      const match = part.match(/^\[(S\d+)\]$/);
      const source = match && sources.find((item) => item.citation_id === match[1]);
      if (source) return <button className="citation" key={`${part}-${index}`} onClick={() => onCitation(source)} aria-label={`Open source ${source.citation_id}`}>{part}</button>;
      return <ReactMarkdown key={`${part}-${index}`} remarkPlugins={[remarkGfm]}>{part}</ReactMarkdown>;
    })}
  </div>;
}
