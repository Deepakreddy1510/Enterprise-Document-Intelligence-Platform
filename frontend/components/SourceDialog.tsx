"use client";
import { useEffect, useRef } from "react";
import type { Source } from "../types";
export function SourceDialog({ source, onClose }: { source: Source | null; onClose: () => void }) {
 const closeRef=useRef<HTMLButtonElement>(null);
 useEffect(()=>{if(source) closeRef.current?.focus(); const f=(e:KeyboardEvent)=>{if(e.key==="Escape")onClose()};addEventListener("keydown",f);return()=>removeEventListener("keydown",f)},[source,onClose]);
 if(!source)return null;
 return <div className="dialog-backdrop" role="presentation" onMouseDown={onClose}><section className="source-dialog" role="dialog" aria-modal="true" aria-label={`Source ${source.citation_id}`} onMouseDown={e=>e.stopPropagation()}><button ref={closeRef} onClick={onClose} aria-label="Close source details">Close</button><h2>{source.citation_id} · {source.document_name ?? "Selected document"}</h2><p>Page {source.page} · similarity {source.similarity.toFixed(3)}</p><pre>{source.content}</pre></section></div>
}
