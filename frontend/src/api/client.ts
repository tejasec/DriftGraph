import {
  GraphPayload,
  Community,
  GraphStats
} from '@/types/graph';
import {
  NoteSummary,
  NoteDetail,
  NoteCreateRequest,
  NoteUpdateRequest,
  TemplateItem
} from '@/types/notes';
import {
  GraphAnalyticsReport,
  PathResult
} from '@/types/analytics';
import {
  ClassificationResult,
  VoiceRequest,
  VoiceResponse,
  QueryRequest,
  QueryResponse,
  BatchUploadResponse,
  OCRCorrectionRequest,
  WebScrapeRequest
} from '@/types/modals';

async function fetchJson<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
    ...options,
  });

  if (!res.ok) {
    let errMessage = `HTTP ${res.status} ${res.statusText}`;
    try {
      const errData = await res.json();
      if (errData && errData.detail) {
        errMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Ignore JSON parse failure on non-JSON error
    }
    throw new Error(errMessage);
  }

  return res.json();
}

export const graphApi = {
  getElements: (threshold?: number): Promise<GraphPayload> => {
    const q = threshold !== undefined ? `?threshold=${threshold}` : '';
    return fetchJson<GraphPayload>(`/api/graph${q}`);
  },

  getCommunities: (level?: number): Promise<Community[]> => {
    const q = level !== undefined ? `?level=${level}` : '';
    return fetchJson<Community[]>(`/api/graph/communities${q}`);
  },

  computeLayout: (engine = 'galaxy', iterations = 500, recompute = false): Promise<GraphPayload> => {
    return fetchJson<GraphPayload>(
      `/api/graph/layout?engine=${engine}&iterations=${iterations}&recompute=${recompute}`,
      { method: 'POST' }
    );
  },

  getStats: (threshold?: number): Promise<GraphStats> => {
    const q = threshold !== undefined ? `?threshold=${threshold}` : '';
    return fetchJson<GraphStats>(`/api/graph/stats${q}`);
  },
};

export const notesApi = {
  listNotes: (includeDeleted = false): Promise<NoteSummary[]> => {
    return fetchJson<NoteSummary[]>(`/api/notes?include_deleted=${includeDeleted}`);
  },

  getNote: (noteId: string): Promise<NoteDetail> => {
    return fetchJson<NoteDetail>(`/api/notes/${encodeURIComponent(noteId)}`);
  },

  createNote: (req: NoteCreateRequest): Promise<NoteDetail> => {
    return fetchJson<NoteDetail>('/api/notes', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  updateNote: (noteId: string, req: NoteUpdateRequest): Promise<NoteDetail> => {
    return fetchJson<NoteDetail>(`/api/notes/${encodeURIComponent(noteId)}`, {
      method: 'PUT',
      body: JSON.stringify(req),
    });
  },

  deleteNote: (noteId: string, permanent = false): Promise<{ message: string; note_id: string; permanent: boolean }> => {
    return fetchJson<{ message: string; note_id: string; permanent: boolean }>(
      `/api/notes/${encodeURIComponent(noteId)}?permanent=${permanent}`,
      { method: 'DELETE' }
    );
  },

  bulkDelete: (noteIds: string[], permanent = false): Promise<{ deleted_count: number; permanent: boolean }> => {
    return fetchJson<{ deleted_count: number; permanent: boolean }>('/api/notes/bulk-delete', {
      method: 'POST',
      body: JSON.stringify({ note_ids: noteIds, permanent }),
    });
  },

  undoDelete: (noteId: string): Promise<NoteDetail> => {
    return fetchJson<NoteDetail>(`/api/notes/${encodeURIComponent(noteId)}/undo`, {
      method: 'POST',
    });
  },

  bulkUndo: (noteIds: string[]): Promise<{ restored_count: number }> => {
    return fetchJson<{ restored_count: number }>('/api/notes/bulk-undo', {
      method: 'POST',
      body: JSON.stringify({ note_ids: noteIds }),
    });
  },

  emptyTrash: (): Promise<{ purged_count: number }> => {
    return fetchJson<{ purged_count: number }>('/api/notes/empty-trash', {
      method: 'POST',
    });
  },

  listTemplates: (): Promise<TemplateItem[]> => {
    return fetchJson<TemplateItem[]>('/api/notes/templates');
  },

  instantiateTemplate: (
    templateId: string,
    values: Record<string, string>,
    customTitle?: string
  ): Promise<NoteDetail> => {
    return fetchJson<NoteDetail>(`/api/notes/templates/${templateId}/instantiate`, {
      method: 'POST',
      body: JSON.stringify({ values, custom_title: customTitle }),
    });
  },
};

export const analyticsApi = {
  getReport: (): Promise<GraphAnalyticsReport> => {
    return fetchJson<GraphAnalyticsReport>('/api/graph/analytics');
  },

  findPath: (source: string, target: string): Promise<PathResult> => {
    return fetchJson<PathResult>('/api/graph/analytics/path', {
      method: 'POST',
      body: JSON.stringify({ source, target }),
    });
  },

  getQuestions: (): Promise<any[]> => {
    return fetchJson<any[]>('/api/graph/analytics/questions');
  },
};

export const queryApi = {
  ask: (req: QueryRequest): Promise<QueryResponse> => {
    return fetchJson<QueryResponse>('/api/query', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },
};

export const voiceApi = {
  ask: (req: VoiceRequest): Promise<VoiceResponse> => {
    return fetchJson<VoiceResponse>('/api/voice/ask', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  getAudioUrl: (audioId: string): string => `/api/voice/audio/${encodeURIComponent(audioId)}`,
};

export const ocrApi = {
  uploadDocuments: async (formData: FormData): Promise<BatchUploadResponse> => {
    const res = await fetch('/api/ingest/ocr/batch', {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  correctText: (req: OCRCorrectionRequest): Promise<{ status: string; message: string }> => {
    return fetchJson<{ status: string; message: string }>('/api/ingest/ocr/correct', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },

  rebuildPipeline: (): Promise<any> => {
    return fetchJson('/api/ingest', {
      method: 'POST',
      body: JSON.stringify({ rebuild: true }),
    });
  },
};

export const classifyApi = {
  classifyText: (text: string, filename = 'document.txt'): Promise<ClassificationResult> => {
    return fetchJson<ClassificationResult>('/api/classify', {
      method: 'POST',
      body: JSON.stringify({ text, filename }),
    });
  },

  classifyFile: async (file: File): Promise<ClassificationResult> => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/classify/file', {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${res.status}`);
    }
    return res.json();
  },

  classifyNote: (noteId: string, updateTags = false): Promise<ClassificationResult> => {
    return fetchJson<ClassificationResult>(
      `/api/classify/note/${encodeURIComponent(noteId)}?update_tags=${updateTags}`,
      { method: 'POST' }
    );
  },
};

export const sourcesApi = {
  scrapeUrl: (req: WebScrapeRequest): Promise<any> => {
    return fetchJson('/api/ingest/web', {
      method: 'POST',
      body: JSON.stringify(req),
    });
  },
};

export const statusApi = {
  health: (): Promise<{ status: string; app: string; version: string }> => {
    return fetchJson<{ status: string; app: string; version: string }>('/health');
  },

  diagnostics: (): Promise<any> => {
    return fetchJson('/api/status/diagnostics');
  },
};
