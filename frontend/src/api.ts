import type {
  AccountRecord,
  BriefingNote,
  BriefingRequest,
  DataSourceInfo,
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

export class ApiError extends Error {
  kind: 'backend-unavailable' | 'request-failed';
  status?: number;

  constructor(message: string, kind: 'backend-unavailable' | 'request-failed', status?: number) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
  }
}

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  if (!hasApiBaseUrl()) {
    throw new ApiError('API base URL is not configured.', 'backend-unavailable');
  }
  let response: Response;
  try {
    response = await fetch(`${getApiBaseUrl()}${path}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {})
      },
      ...init
    });
  } catch {
    throw new ApiError('Backend unavailable.', 'backend-unavailable');
  }
  if (!response.ok) {
    throw new ApiError(`Request failed with status ${response.status}`, 'request-failed', response.status);
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

export async function fetchDataSource(): Promise<DataSourceInfo> {
  return requestJson<DataSourceInfo>('/data-source');
}

export async function exportExamples(): Promise<ExportExamplesResponse & { artifacts: ExportArtifacts }> {
  return requestJson<ExportExamplesResponse & { artifacts: ExportArtifacts }>('/export/examples', {
    method: 'POST',
    body: JSON.stringify({})
  });
}
