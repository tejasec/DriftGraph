export interface NoteSummary {
  id: string;
  filename: string;
  title: string;
  date: string;
  source_type: string;
  tags: string[];
  word_count: number;
  char_count: number;
  preview: string;
  top_category?: string | null;
  connected_entities_count: number;
  deleted_at?: string | null;
}

export interface NoteDetail {
  id: string;
  filename: string;
  title: string;
  date: string;
  source_type: string;
  tags: string[];
  content: string;
  metadata: Record<string, any>;
  word_count: number;
  char_count: number;
  top_category?: string | null;
  connected_entities: Array<{ name: string; type?: string; community?: number; [key: string]: any }>;
  deleted_at?: string | null;
}

export interface NoteCreateRequest {
  title?: string;
  content?: string;
  tags?: string[];
  source_type?: string;
}

export interface NoteUpdateRequest {
  content: string;
  title?: string;
  tags?: string[];
}

export interface TemplateItem {
  id: string;
  name: string;
  description: string;
  fields: Array<{ name: string; label: string; placeholder?: string }>;
}
