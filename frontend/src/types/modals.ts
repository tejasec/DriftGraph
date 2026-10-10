export interface CategoryScore {
  category: string;
  percentage: number;
  raw_score: number;
  matched_keywords: string[];
  progress_bar: string;
}

export interface ContextualEntity {
  entity: string;
  category: string;
  origin_url?: string | null;
  search_url?: string | null;
  connected_concepts: string[];
}

export interface ClassificationResult {
  filename: string;
  word_count: number;
  char_count: number;
  line_count: number;
  top_category: string;
  categories: CategoryScore[];
  ascii_box: string;
  auto_tags: string[];
  sentiment: string;
  sentiment_score: number;
  priority: string;
  contextual_entities: ContextualEntity[];
}

export interface VoiceRequest {
  query: string;
  session_id?: string;
  voice_id?: string;
  mode?: string;
  quick_answer?: boolean;
  quick_mode?: boolean;
  language?: string;
}

export interface VoiceResponse {
  query: string;
  text_answer: string;
  answer?: string;
  audio_base64?: string | null;
  audio_url?: string | null;
  duration_sec: number;
  session_id?: string | null;
  mode_used: string;
  sources: Array<Record<string, any>>;
  citations: Array<Record<string, any>>;
  cited_node_ids: string[];
}

export interface Citation {
  source_type: "chunk" | "community" | "node";
  id: string;
  title?: string;
  text_snippet: string;
  score: number;
}

export interface QueryRequest {
  query: string;
  mode?: "auto" | "global" | "local";
  top_k?: number;
  stream?: boolean;
}

export interface QueryResponse {
  query: string;
  mode_used: "global" | "local";
  answer: string;
  citations: Citation[];
  confidence: number;
  latency_ms: number;
  retrieval_trace?: Record<string, any>;
}

export interface OCRPageResult {
  filename: string;
  saved_note?: string;
  status: "success" | "failed";
  error?: string;
  pages_count: number;
  mean_confidence: number;
  errors_count: number;
  tables_count: number;
  title?: string;
}

export interface BatchUploadResponse {
  total_documents: number;
  successful_documents: number;
  failed_documents: number;
  total_pages: number;
  mean_confidence: number;
  total_errors_marked: number;
  total_tables_detected: number;
  documents: OCRPageResult[];
  message: string;
}

export interface OCRCorrectionRequest {
  filename: string;
  old_text: string;
  new_text: string;
}

export interface WebScrapeRequest {
  url: string;
  custom_title?: string;
  auto_classify?: boolean;
}
