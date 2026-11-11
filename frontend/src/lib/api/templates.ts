export interface TemplateRedFlag {
  id: string;
  label: string;
  explanation: string;
}

export interface TemplateSummary {
  id: string;
  family_id: string;
  version: number;
  name: string;
  sender: string;
  subject: string;
  body: string;
  difficulty: 'easy' | 'medium' | 'hard';
  attack_technique_id: string;
  lure_type: string;
  status: 'draft' | 'published' | 'archived';
  is_demo: boolean;
  red_flag_count: number;
  red_flags: TemplateRedFlag[];
  created_at: string | null;
  updated_at: string | null;
}

export interface TemplatePreview {
  html: string;
  name: string;
  sender: string;
  subject: string;
  difficulty: 'easy' | 'medium' | 'hard';
  attack_technique_id: string;
  version: number;
  red_flags: TemplateRedFlag[];
}

export interface TemplateListResponse {
  templates: TemplateSummary[];
  total: number;
}

export interface TemplateFilters {
  search?: string;
  difficulty?: string;
  technique?: string;
  status?: string;
}

export function templateSearchParams(filters: TemplateFilters): string {
  const params = new URLSearchParams();
  if (filters.search?.trim()) params.set('search', filters.search.trim());
  if (filters.difficulty) params.set('difficulty', filters.difficulty);
  if (filters.technique?.trim()) params.set('technique', filters.technique.trim());
  if (filters.status) params.set('status', filters.status);
  const query = params.toString();
  return query ? `?${query}` : '';
}

export async function fetchTemplates(
  filters: TemplateFilters,
  signal?: AbortSignal,
): Promise<TemplateListResponse> {
  const response = await fetch(
    `/api/v1/templates${templateSearchParams(filters)}`,
    { cache: 'no-store', signal },
  );
  if (!response.ok) {
    throw new Error(`Template request failed with ${response.status}`);
  }
  return (await response.json()) as TemplateListResponse;
}

export async function fetchTemplatePreview(
  templateId: string,
  signal?: AbortSignal,
): Promise<TemplatePreview> {
  const response = await fetch(`/api/v1/templates/${templateId}/preview`, {
    cache: 'no-store',
    signal,
  });
  if (!response.ok) {
    throw new Error(`Preview request failed with ${response.status}`);
  }
  const data = (await response.json()) as { preview?: TemplatePreview };
  if (!data.preview) {
    throw new Error('Preview payload was empty');
  }
  return data.preview;
}
