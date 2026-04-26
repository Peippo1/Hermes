import type {
  AccountRecord,
  BriefingNote,
  BriefingRequest,
  ExportExamplesResponse,
  ExportArtifacts,
  OutreachDraft,
  OutreachRequest,
  QueueItem,
  QueueOutreachRequest,
  QueueResponse
} from './types';

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.trim() ?? '';

function trimSlash(value: string): string {
  return value.replace(/\/$/, '');
}

export function hasApiBaseUrl(): boolean {
  return baseUrl.length > 0;
}

export function getApiBaseUrl(): string {
  return trimSlash(baseUrl);
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  if (!hasApiBaseUrl()) {
    throw new Error('API base URL is not configured.');
  }
  const response = await fetch(`${getApiBaseUrl()}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {})
    },
    ...init
  });
  if (!response.ok) {
    throw new Error(`Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchAccounts(): Promise<AccountRecord[]> {
  const payload = await requestJson<{ accounts: AccountRecord[] }>('/accounts');
  return payload.accounts;
}

export async function generateOutreach(request: OutreachRequest): Promise<OutreachDraft> {
  return requestJson<OutreachDraft>('/generate/outreach', {
    method: 'POST',
    body: JSON.stringify(request)
  });
}

export async function generateBriefing(request: BriefingRequest): Promise<BriefingNote> {
  return requestJson<BriefingNote>('/generate/briefing', {
    method: 'POST',
    body: JSON.stringify(request)
  });
}

export async function queueOutreach(request: QueueOutreachRequest): Promise<{ item: QueueItem; queue_size: number }> {
  return requestJson<{ item: QueueItem; queue_size: number }>('/queue/outreach', {
    method: 'POST',
    body: JSON.stringify(request)
  });
}

export async function fetchQueue(): Promise<QueueResponse> {
  return requestJson<QueueResponse>('/queue');
}

export async function exportExamples(): Promise<ExportExamplesResponse & { artifacts: ExportArtifacts }> {
  return requestJson<ExportExamplesResponse & { artifacts: ExportArtifacts }>('/export/examples', {
    method: 'POST',
    body: JSON.stringify({})
  });
}

