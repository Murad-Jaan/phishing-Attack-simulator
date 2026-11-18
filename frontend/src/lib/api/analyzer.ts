export interface AnalyzerFinding {
  rule_id: string;
  reason: string;
  weight: number;
  category: string;
}

export interface AnalyzerLink {
  host: string;
  text: string;
}

export interface AnalyzerAnalysis {
  score: number;
  label: 'Safe' | 'Suspicious' | 'Likely phishing';
  findings: AnalyzerFinding[];
  rule_ids: string[];
  links: AnalyzerLink[];
  what_to_do: string[];
  parsed: {
    from: string;
    reply_to: string;
    subject: string;
    attachments: string[];
  };
}

export interface AnalyzerPasteInput {
  sender: string;
  subject: string;
  body: string;
  link: string;
  org_domain?: string;
  consent: boolean;
}

export interface AnalyzerErrorFields {
  [field: string]: string;
}

export class AnalyzerApiError extends Error {
  status: number;
  code: string;
  fields: AnalyzerErrorFields;

  constructor(status: number, code: string, message: string, fields: AnalyzerErrorFields) {
    super(message);
    this.name = 'AnalyzerApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

interface ErrorEnvelope {
  error?: {
    code?: string;
    message?: string;
    fields?: AnalyzerErrorFields;
  };
}

async function readError(response: Response): Promise<AnalyzerApiError> {
  let envelope: ErrorEnvelope = {};
  try {
    envelope = (await response.json()) as ErrorEnvelope;
  } catch {
    envelope = {};
  }
  return new AnalyzerApiError(
    response.status,
    envelope.error?.code ?? 'request_failed',
    envelope.error?.message ?? 'The request failed.',
    envelope.error?.fields ?? {},
  );
}

async function csrfToken(): Promise<string> {
  const response = await fetch('/api/v1/auth/csrf', { cache: 'no-store' });
  if (!response.ok) {
    throw new Error('Could not obtain a CSRF token.');
  }
  const data = (await response.json()) as { csrf_token?: string };
  if (!data.csrf_token) {
    throw new Error('CSRF token was missing.');
  }
  return data.csrf_token;
}

export async function analyzePaste(
  input: AnalyzerPasteInput,
  signal?: AbortSignal,
): Promise<AnalyzerAnalysis> {
  const token = await csrfToken();
  const response = await fetch('/api/v1/analyzer', {
    method: 'POST',
    cache: 'no-store',
    signal,
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': token,
    },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    throw await readError(response);
  }
  const data = (await response.json()) as { analysis?: AnalyzerAnalysis };
  if (!data.analysis) {
    throw new Error('Analysis payload was empty.');
  }
  return data.analysis;
}

export async function analyzeEml(
  file: File,
  consent: boolean,
  orgDomain?: string,
  signal?: AbortSignal,
): Promise<AnalyzerAnalysis> {
  const token = await csrfToken();
  const form = new FormData();
  form.set('file', file);
  form.set('consent', String(consent));
  if (orgDomain) {
    form.set('org_domain', orgDomain);
  }
  const response = await fetch('/api/v1/analyzer', {
    method: 'POST',
    cache: 'no-store',
    signal,
    headers: { 'X-CSRF-Token': token },
    body: form,
  });
  if (!response.ok) {
    throw await readError(response);
  }
  const data = (await response.json()) as { analysis?: AnalyzerAnalysis };
  if (!data.analysis) {
    throw new Error('Analysis payload was empty.');
  }
  return data.analysis;
}

export async function reportAnalysis(
  label: AnalyzerAnalysis['label'],
  ruleIds: string[],
): Promise<{ ok: boolean; report_id: string }> {
  const token = await csrfToken();
  const response = await fetch('/api/v1/analyzer/report', {
    method: 'POST',
    cache: 'no-store',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': token,
    },
    body: JSON.stringify({ label, rule_ids: ruleIds }),
  });
  if (!response.ok) {
    throw await readError(response);
  }
  return (await response.json()) as { ok: boolean; report_id: string };
}
