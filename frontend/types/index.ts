export type Document = { id: string; original_filename: string; status: "pending"|"processing"|"ready"|"failed"; processing_error?: string|null; page_count: number; chunk_count: number; created_at: string };
export type Source = { citation_id: string; document_id?: string; document_name?: string; page: number; chunk_id: string; chunk_index?: number; similarity: number; content: string };
export type ChatMessage = { id: string; role: "user"|"assistant"; content: string; created_at: string; sources: Source[] };
export type Conversation = { id: string; title: string; created_at?: string; documents?: string[]; messages?: ChatMessage[] };
