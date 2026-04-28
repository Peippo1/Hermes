import { useEffect, useMemo, useState } from 'react';
import {
  buildMockArtifacts,
  buildMockExport,
  buildMockQueue,
  enqueueMockOutreach,
  generateMockBriefing,
  generateMockOutreach,
  getMockAccounts
} from './mockData';
import {
  ApiError,
  exportExamples,
  fetchDataSource,
  fetchAccounts,
  fetchQueue,
  generateBriefing,
  generateOutreach,
  getApiBaseUrl,
  hasApiBaseUrl,
  queueOutreach
} from './api';
import type {
  AccountRecord,
  BriefingNote,
  DataSourceInfo,
  ExportArtifacts,
  OutreachDraft,
  QueueItem,
  BriefingFocus,
  Channel,
  Tone
} from './types';

type Mode = 'api' | 'mock';
type ConnectionState = 'loading' | 'connected' | 'mock' | 'backend-unavailable' | 'request-failed';
type ActionLoadingState = {
  outreach: boolean;
  briefing: boolean;
  queue: boolean;
  export: boolean;
  queueView: boolean;
};

const SESSION_STORAGE_KEY = 'hermes.frontend.controls.v1';

function loadSessionControls(): {
  selectedAccountId: string;
  selectedChannel: Channel;
  selectedTone: Tone;
  selectedFocus: BriefingFocus;
} {
  if (typeof window === 'undefined') {
    return {
      selectedAccountId: '',
      selectedChannel: 'email',
      selectedTone: 'concise',
      selectedFocus: 'commercial'
    };
  }

  try {
    const raw = window.sessionStorage.getItem(SESSION_STORAGE_KEY);
    if (!raw) {
      return {
        selectedAccountId: '',
        selectedChannel: 'email',
        selectedTone: 'concise',
        selectedFocus: 'commercial'
      };
    }
    const parsed = JSON.parse(raw) as Partial<{
      selectedAccountId: string;
      selectedChannel: Channel;
      selectedTone: Tone;
      selectedFocus: BriefingFocus;
    }>;
    return {
      selectedAccountId: parsed.selectedAccountId ?? '',
      selectedChannel: parsed.selectedChannel ?? 'email',
      selectedTone: parsed.selectedTone ?? 'concise',
      selectedFocus: parsed.selectedFocus ?? 'commercial'
    };
  } catch {
    return {
      selectedAccountId: '',
      selectedChannel: 'email',
      selectedTone: 'concise',
      selectedFocus: 'commercial'
    };
  }
}

function formatNumber(value?: number | null): string {
  if (value === null || value === undefined) return 'Not provided';
  return new Intl.NumberFormat('en-GB').format(value);
}

function formatMoney(value?: number | null): string {
  if (value === null || value === undefined) return 'Not provided';
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    maximumFractionDigits: 0
  }).format(value);
}

function formatDollar(value?: number | null): string {
  if (value === null || value === undefined) return 'Not provided';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(value);
}

function formatCompactNumber(value?: number | null): string {
  if (value === null || value === undefined) return '—';
  const amount = Math.abs(value);
  if (amount >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1).replace(/\.0$/, '')}m`;
  }
  if (amount >= 1_000) {
    return `${(value / 1_000).toFixed(1).replace(/\.0$/, '')}k`;
  }
  return `${value}`;
}

function formatCompactDollar(value?: number | null): string {
  if (value === null || value === undefined) return '—';
  const amount = Math.abs(value);
  if (amount >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1).replace(/\.0$/, '')}m`;
  }
  if (amount >= 1_000) {
    return `$${(value / 1_000).toFixed(1).replace(/\.0$/, '')}k`;
  }
  return `$${value}`;
}

function joinList(values: string[] | undefined): string {
  return values && values.length > 0 ? values.join(' • ') : 'None';
}

function accountOptionLabel(account: AccountRecord): string {
  const parts: string[] = [account.company_name];
  if (account.number_of_sites !== null && account.number_of_sites !== undefined) {
    parts.push(`${formatCompactNumber(account.number_of_sites)} site${account.number_of_sites === 1 ? '' : 's'}`);
  }
  if (account.estimated_annual_visits !== null && account.estimated_annual_visits !== undefined) {
    parts.push(`${formatCompactNumber(account.estimated_annual_visits)} visits`);
  }
  if (account.contact_role) {
    parts.push(account.contact_role);
  }
  return parts.join(' · ');
}

function renderMessagePreview(message: string): JSX.Element[] {
  return message
    .split(/\n{2,}/)
    .map((paragraph, index) => (
      <p key={`msg-${index}`} className="message-paragraph">
        {paragraph}
      </p>
    ));
}

function renderBriefingMarkdown(markdown: string): JSX.Element[] {
  const blocks: JSX.Element[] = [];
  const lines = markdown.split('\n');
  let paragraph: string[] = [];
  let listItems: string[] = [];
  let objection: { objection: string; response: string } | null = null;

  function flushParagraph() {
    if (paragraph.length === 0) return;
    blocks.push(
      <p key={`p-${blocks.length}`} className="briefing-paragraph">
        {paragraph.join(' ')}
      </p>
    );
    paragraph = [];
  }

  function flushList() {
    if (listItems.length === 0) return;
    blocks.push(
      <ul key={`ul-${blocks.length}`} className="briefing-list">
        {listItems.map((item, index) => (
          <li key={`li-${blocks.length}-${index}`}>{item}</li>
        ))}
      </ul>
    );
    listItems = [];
  }

  function flushObjection() {
    if (!objection) return;
    blocks.push(
      <div key={`objection-${blocks.length}`} className="objection-block">
        <div className="objection-line">
          <span className="briefing-label">Objection:</span>
          <span>{objection.objection}</span>
        </div>
        <div className="response-line">
          <span className="briefing-label">Response:</span>
          <span>{objection.response}</span>
        </div>
      </div>
    );
    objection = null;
  }

  function flush() {
    flushParagraph();
    flushList();
    flushObjection();
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      flush();
      continue;
    }

    const headingMatch = line.match(/^(#{1,3})\s+(.*)$/);
    if (headingMatch) {
      flush();
      const level = headingMatch[1].length;
      const Tag = `h${Math.min(level, 3)}` as keyof JSX.IntrinsicElements;
      blocks.push(
        <Tag key={`h-${blocks.length}`} className={`briefing-heading briefing-heading-${Tag}`}>
          {headingMatch[2]}
        </Tag>
      );
      continue;
    }

    if (line.startsWith('- **Objection:**') || line.startsWith('**Objection:**') || line.startsWith('Objection:') || line.startsWith('- Objection:')) {
      flushParagraph();
      flushList();
      flushObjection();
      objection = {
        objection: line
          .replace(/^- \*\*Objection:\*\*\s*/, '')
          .replace(/^\*\*Objection:\*\*\s*/, '')
          .replace(/^- /, '')
          .replace(/^Objection:\s*/, ''),
        response: ''
      };
      continue;
    }

    if ((line.startsWith('**Response:**') || line.startsWith('Response:')) && objection) {
      objection.response = line.replace(/^\*\*Response:\*\*\s*/, '').replace(/^Response:\s*/, '');
      continue;
    }

    if (objection) {
      if (!objection.response) {
        objection.response = line;
        continue;
      }
      flushObjection();
      paragraph.push(line);
      continue;
    }

    if (line.startsWith('- ')) {
      flushParagraph();
      listItems.push(line.slice(2).trim());
      continue;
    }

    paragraph.push(line);
  }

  flush();
  return blocks;
}

function initialLoadingState(): ActionLoadingState {
  return {
    outreach: false,
    briefing: false,
    queue: false,
    export: false,
    queueView: false
  };
}

function fallbackMessage(kind: 'backend-unavailable' | 'request-failed'): string {
  return kind === 'backend-unavailable'
    ? 'Backend unavailable. Using mock mode.'
    : 'Request failed. Using mock mode.';
}

function actionLabel(kind: keyof ActionLoadingState): string {
  return {
    outreach: 'Generating outreach…',
    briefing: 'Generating briefing…',
    queue: 'Adding to queue…',
    export: 'Exporting examples…',
    queueView: 'Viewing queue…'
  }[kind];
}

export default function App() {
  const initialControls = loadSessionControls();
  const [mode, setMode] = useState<Mode>('mock');
  const [connectionState, setConnectionState] = useState<ConnectionState>('loading');
  const [statusMessage, setStatusMessage] = useState<string>('Loading account data.');
  const [actionError, setActionError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<AccountRecord[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>(initialControls.selectedAccountId);
  const [selectedChannel, setSelectedChannel] = useState<Channel>(initialControls.selectedChannel);
  const [selectedTone, setSelectedTone] = useState<Tone>(initialControls.selectedTone);
  const [selectedFocus, setSelectedFocus] = useState<BriefingFocus>(initialControls.selectedFocus);
  const [outreach, setOutreach] = useState<OutreachDraft | null>(null);
  const [briefing, setBriefing] = useState<BriefingNote | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [queueSize, setQueueSize] = useState<number>(0);
  const [artifacts, setArtifacts] = useState<ExportArtifacts | null>(null);
  const [dataSourceInfo, setDataSourceInfo] = useState<DataSourceInfo | null>(null);
  const [loading, setLoading] = useState<ActionLoadingState>(initialLoadingState);

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.account_id === selectedAccountId) ?? null,
    [accounts, selectedAccountId]
  );
  const connectionAlert =
    connectionState === 'backend-unavailable' || connectionState === 'request-failed' ? statusMessage : null;
  const statusLabel = mode === 'api' ? 'Live mode' : 'Mock mode';

  const apiBaseUrl = hasApiBaseUrl() ? getApiBaseUrl() : 'Not configured';

  useEffect(() => {
    try {
      window.sessionStorage.setItem(
        SESSION_STORAGE_KEY,
        JSON.stringify({
          selectedAccountId,
          selectedChannel,
          selectedTone,
          selectedFocus
        })
      );
    } catch {
      // Session storage is best-effort only.
    }
  }, [selectedAccountId, selectedChannel, selectedTone, selectedFocus]);

  function setLoadingFlag(key: keyof ActionLoadingState, value: boolean) {
    setLoading((current) => ({ ...current, [key]: value }));
  }

  function clearLocalQueueView() {
    setActionError(null);
    setQueue([]);
    setQueueSize(0);
  }

  function switchToMock(
    kind: 'mock' | 'backend-unavailable' | 'request-failed',
    accountsForMock: AccountRecord[]
  ) {
    const mockQueue = buildMockQueue(accountsForMock);
    setMode('mock');
    setConnectionState(kind);
    setStatusMessage(kind === 'mock' ? 'Mock mode is active. No API base URL is configured.' : fallbackMessage(kind));
    setAccounts(accountsForMock);
    setSelectedAccountId(accountsForMock[0]?.account_id ?? '');
    setQueue(mockQueue.items);
    setQueueSize(mockQueue.queue_size);
    setDataSourceInfo({
      data_source: 'sample_fallback',
      data_source_detail: 'data/sample_accounts.csv',
      data_load_warning: kind === 'mock' ? null : fallbackMessage(kind),
      loaded_accounts: accountsForMock.length
    });
  }

  useEffect(() => {
    let cancelled = false;

    async function loadAccounts() {
      if (!hasApiBaseUrl()) {
        if (cancelled) return;
        const mockAccounts = getMockAccounts();
        switchToMock('mock', mockAccounts);
        return;
      }

      setConnectionState('loading');
      setStatusMessage('Connecting to the backend.');

      try {
        const [remoteAccounts, remoteQueue, remoteDataSource] = await Promise.all([
          fetchAccounts(),
          fetchQueue(),
          fetchDataSource()
        ]);
        if (cancelled) return;
        setMode('api');
        setConnectionState('connected');
        setStatusMessage('Connected to the backend.');
        setAccounts(remoteAccounts);
        setSelectedAccountId(remoteAccounts[0]?.account_id ?? '');
        setQueue(remoteQueue.items);
        setQueueSize(remoteQueue.queue_size);
        setDataSourceInfo(remoteDataSource);
      } catch (error) {
        if (cancelled) return;
        const mockAccounts = getMockAccounts();
        const kind = error instanceof ApiError && error.kind === 'request-failed' ? 'request-failed' : 'backend-unavailable';
        switchToMock(kind, mockAccounts);
      }
    }

    loadAccounts();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleGenerateOutreach() {
    if (!selectedAccount) return;
    setActionError(null);
    setLoadingFlag('outreach', true);
    try {
      const request = {
        account_id: selectedAccount.account_id,
        channel: selectedChannel,
        tone: selectedTone
      };
      if (mode === 'mock') {
        setOutreach(generateMockOutreach(selectedAccount, request));
        return;
      }
      setOutreach(await generateOutreach(request));
    } catch (error) {
      const kind = error instanceof ApiError && error.kind === 'request-failed' ? 'request-failed' : 'backend-unavailable';
      setActionError(fallbackMessage(kind));
      switchToMock(kind, accounts.length > 0 ? accounts : getMockAccounts());
      setOutreach(generateMockOutreach(selectedAccount, {
        account_id: selectedAccount.account_id,
        channel: selectedChannel,
        tone: selectedTone
      }));
    } finally {
      setLoadingFlag('outreach', false);
    }
  }

  async function handleGenerateBriefing() {
    if (!selectedAccount) return;
    setActionError(null);
    setLoadingFlag('briefing', true);
    try {
      const request = {
        account_id: selectedAccount.account_id,
        focus: selectedFocus
      };
      if (mode === 'mock') {
        setBriefing(generateMockBriefing(selectedAccount, request));
        return;
      }
      setBriefing(await generateBriefing(request));
    } catch (error) {
      const kind = error instanceof ApiError && error.kind === 'request-failed' ? 'request-failed' : 'backend-unavailable';
      setActionError(fallbackMessage(kind));
      switchToMock(kind, accounts.length > 0 ? accounts : getMockAccounts());
      setBriefing(generateMockBriefing(selectedAccount, {
        account_id: selectedAccount.account_id,
        focus: selectedFocus
      }));
    } finally {
      setLoadingFlag('briefing', false);
    }
  }

  async function handleQueueOutreach() {
    if (!selectedAccount) return;
    setActionError(null);
    setLoadingFlag('queue', true);
    try {
      if (mode === 'mock') {
        const item = enqueueMockOutreach(selectedAccount, {
          account_id: selectedAccount.account_id,
          channel: selectedChannel,
          tone: selectedTone
        });
        setQueue((current) => [item, ...current]);
        setQueueSize((current) => current + 1);
        if (!outreach) {
          setOutreach(generateMockOutreach(selectedAccount, {
            account_id: selectedAccount.account_id,
            channel: selectedChannel,
            tone: selectedTone
          }));
        }
        return;
      }
      const response = await queueOutreach({
        account_id: selectedAccount.account_id,
        channel: selectedChannel,
        tone: selectedTone
      });
      setQueue((current) => [response.item, ...current]);
      setQueueSize(response.queue_size);
      if (!outreach) {
        setOutreach(await generateOutreach({
          account_id: selectedAccount.account_id,
          channel: selectedChannel,
          tone: selectedTone
        }));
      }
    } catch (error) {
      const kind = error instanceof ApiError && error.kind === 'request-failed' ? 'request-failed' : 'backend-unavailable';
      setActionError(fallbackMessage(kind));
      switchToMock(kind, accounts.length > 0 ? accounts : getMockAccounts());
      const item = enqueueMockOutreach(selectedAccount, {
        account_id: selectedAccount.account_id,
        channel: selectedChannel,
        tone: selectedTone
      });
      setQueue((current) => [item, ...current]);
      setQueueSize((current) => current + 1);
      if (!outreach) {
        setOutreach(generateMockOutreach(selectedAccount, {
          account_id: selectedAccount.account_id,
          channel: selectedChannel,
          tone: selectedTone
        }));
      }
    } finally {
      setLoadingFlag('queue', false);
    }
  }

  async function handleViewQueue() {
    setActionError(null);
    setLoadingFlag('queueView', true);
    try {
      if (mode === 'mock') {
        const response = buildMockQueue(accounts);
        setQueue(response.items);
        setQueueSize(response.queue_size);
        return;
      }
      const response = await fetchQueue();
      setQueue(response.items);
      setQueueSize(response.queue_size);
    } catch (error) {
      const kind = error instanceof ApiError && error.kind === 'request-failed' ? 'request-failed' : 'backend-unavailable';
      setActionError(fallbackMessage(kind));
      switchToMock(kind, accounts.length > 0 ? accounts : getMockAccounts());
      const response = buildMockQueue(accounts.length > 0 ? accounts : getMockAccounts());
      setQueue(response.items);
      setQueueSize(response.queue_size);
    } finally {
      setLoadingFlag('queueView', false);
    }
  }

  async function handleExportExamples() {
    setActionError(null);
    setLoadingFlag('export', true);
    try {
      if (mode === 'mock') {
        if (!selectedAccount) return;
        const exportBundle = buildMockExport(selectedAccount);
        setOutreach(exportBundle.outreach);
        setBriefing(exportBundle.briefing);
        setQueue((current) => [exportBundle.queueItem, ...current]);
        setArtifacts(buildMockArtifacts());
        return;
      }
      const response = await exportExamples();
      setOutreach(response.outreach[0] ?? null);
      setBriefing(response.briefings[0] ?? null);
      setArtifacts(response.artifacts);
    } catch (error) {
      const kind = error instanceof ApiError && error.kind === 'request-failed' ? 'request-failed' : 'backend-unavailable';
      setActionError(fallbackMessage(kind));
      switchToMock(kind, accounts.length > 0 ? accounts : getMockAccounts());
      if (!selectedAccount) return;
      const exportBundle = buildMockExport(selectedAccount);
      setOutreach(exportBundle.outreach);
      setBriefing(exportBundle.briefing);
      setQueue((current) => [exportBundle.queueItem, ...current]);
      setArtifacts(buildMockArtifacts());
    } finally {
      setLoadingFlag('export', false);
    }
  }

  return (
    <div className="shell">
      <main className="app-shell">
        <header className="hero">
          <div className="hero-copy panel">
            <p className="eyebrow">Hermes / AI sales enablement workflow</p>
            <div className="eyebrow-row">
              <span className={`badge ${mode === 'mock' ? 'badge-warning' : 'badge-success'}`}>{statusLabel}</span>
              <span className="status-chip">{connectionState === 'loading' ? 'Loading' : statusMessage}</span>
            </div>
            <h1>AI-assisted outreach, briefing, and review workflows.</h1>
            <p className="subheading">
              Hermes turns account signals into outreach drafts, meeting prep, and a clean review queue with
              deterministic fallback when the backend is unavailable.
            </p>
          </div>
          <div className="hero-metric panel">
            <div className="metric-label">Workflow state</div>
            <div className="metric-value">{selectedAccount?.company_name ?? 'No account selected'}</div>
            <div className="metric-subtle">{selectedAccount?.category ?? 'Choose an account to begin'}</div>
            <div className="hero-mini-row">
              <span className="hero-mini">{mode === 'api' ? 'Live API connected' : 'Mock fallback active'}</span>
              <span className="hero-mini">{queueSize} queued</span>
            </div>
          </div>
        </header>

        <section className="control-bar panel">
          <div className="control-top">
            <div className="field field-account">
              <label htmlFor="account">Account selector</label>
              <select
                id="account"
                value={selectedAccountId}
                onChange={(event) => setSelectedAccountId(event.target.value)}
              >
                {accounts.map((account) => (
                  <option key={account.account_id} value={account.account_id}>
                    {accountOptionLabel(account)}
                  </option>
                ))}
              </select>
            </div>
            <div className="status-panel panel">
              <div>
                <span className="label">Mode</span>
                <p>{mode === 'api' ? 'Real API mode' : 'Mock mode'}</p>
              </div>
              <div>
                <span className="label">Data source</span>
                <p>{dataSourceInfo ? `${dataSourceInfo.data_source === 'google_sheet'
                  ? 'Google Sheet'
                  : dataSourceInfo.data_source === 'local_file'
                    ? 'Local file'
                    : 'Sample fallback'}` : 'Loading...'}</p>
              </div>
              <div>
                <span className="label">Queue</span>
                <p>{queueSize} items</p>
              </div>
              <div className="status-note">Mock queue only — no external messages are sent.</div>
              <details className="technical-details">
                <summary>Technical details</summary>
                <div className="technical-details-body">
                  <span className="label">API base URL</span>
                  <p className="subtle-value">{apiBaseUrl}</p>
                  {dataSourceInfo ? (
                    <p className="subtle-value">{dataSourceInfo.data_source_detail}</p>
                  ) : null}
                </div>
              </details>
            </div>
          </div>

          <div className="control-row">
            <div className="field field-channel">
              <label htmlFor="channel">Channel</label>
              <select id="channel" value={selectedChannel} onChange={(event) => setSelectedChannel(event.target.value as Channel)}>
                <option value="email">Email</option>
                <option value="linkedin">LinkedIn</option>
              </select>
            </div>
            <div className="field field-tone">
              <label htmlFor="tone">Tone</label>
              <select id="tone" value={selectedTone} onChange={(event) => setSelectedTone(event.target.value as Tone)}>
                <option value="concise">Concise</option>
                <option value="warm">Warm</option>
                <option value="direct">Direct</option>
              </select>
            </div>
            <div className="field field-focus">
              <label htmlFor="focus">Briefing focus</label>
              <select
                id="focus"
                value={selectedFocus}
                onChange={(event) => setSelectedFocus(event.target.value as BriefingFocus)}
              >
                <option value="commercial">Commercial</option>
                <option value="operations">Operations</option>
                <option value="growth">Growth</option>
                <option value="customer_support">Customer support</option>
              </select>
            </div>
          </div>

          <p className="control-helper">
            Select an account, adjust the channel and briefing focus, then generate review-ready outputs.
          </p>

          {connectionAlert ? <div className="error-banner">{connectionAlert}</div> : null}
          {actionError ? <div className="error-banner">{actionError}</div> : null}

          <div className="button-row actions">
            <button type="button" className="primary-button" onClick={handleGenerateOutreach} disabled={loading.outreach}>
              {loading.outreach ? actionLabel('outreach') : 'Generate Outreach'}
            </button>
            <button type="button" className="secondary-button" onClick={handleGenerateBriefing} disabled={loading.briefing}>
              {loading.briefing ? actionLabel('briefing') : 'Generate Briefing'}
            </button>
            <button type="button" className="outline-button" onClick={handleQueueOutreach} disabled={loading.queue}>
              {loading.queue ? actionLabel('queue') : 'Add to Mock Queue'}
            </button>
            <button type="button" className="ghost-button" onClick={handleViewQueue} disabled={loading.queueView}>
              {loading.queueView ? actionLabel('queueView') : 'View Queue'}
            </button>
            <button type="button" className="ghost-button" onClick={handleExportExamples} disabled={loading.export}>
              {loading.export ? actionLabel('export') : 'Export Examples'}
            </button>
          </div>
        </section>

        <section className="content-stack">
          <article className="card panel section-card">
            <div className="section-header">
              <div>
                <p className="card-kicker">Account / workflow</p>
                <h2>{selectedAccount?.company_name ?? 'Select an account'}</h2>
              </div>
              <div className="mini-stat">
                <span>Region</span>
                <strong>{selectedAccount?.region ?? 'Not provided'}</strong>
              </div>
            </div>

            {selectedAccount ? (
              <div className="account-profile">
                <div className="profile-strip">
                  <span className="profile-badge">{formatCompactNumber(selectedAccount.number_of_sites)} sites</span>
                  <span className="profile-badge">{formatCompactNumber(selectedAccount.estimated_annual_visits)} visits</span>
                  <span className="profile-badge">{formatCompactDollar(selectedAccount.estimated_average_ticket_price)} avg ticket</span>
                  <span className="profile-badge">{formatCompactDollar(selectedAccount.estimated_transaction_volume)} volume</span>
                </div>
                <div className="preview-grid">
                <div>
                  <span className="label">Category</span>
                  <p>{selectedAccount.category ?? 'Not provided'}</p>
                </div>
                <div>
                  <span className="label">Sub-category</span>
                  <p>{selectedAccount.sub_category ?? 'Not provided'}</p>
                </div>
                <div>
                  <span className="label">HQ location</span>
                  <p>{selectedAccount.hq_location ?? 'Not provided'}</p>
                </div>
                <div>
                  <span className="label">Sites</span>
                  <p>{formatNumber(selectedAccount.number_of_sites)}</p>
                </div>
                <div>
                  <span className="label">Annual visits</span>
                  <p>{formatNumber(selectedAccount.estimated_annual_visits)}</p>
                </div>
                <div>
                  <span className="label">Avg ticket</span>
                  <p>{formatDollar(selectedAccount.estimated_average_ticket_price)}</p>
                </div>
                <div>
                  <span className="label">Est. transaction volume</span>
                  <p>{formatDollar(selectedAccount.estimated_transaction_volume)}</p>
                </div>
                {selectedAccount.estimated_annual_revenue !== null && selectedAccount.estimated_annual_revenue !== undefined ? (
                  <div>
                    <span className="label">Est. Easol revenue</span>
                    <p>{formatDollar(selectedAccount.estimated_annual_revenue)}</p>
                  </div>
                ) : null}
                <div className="contact-block">
                  <span className="label">Contact</span>
                  <p>{selectedAccount.contact_name ?? 'Not provided'}</p>
                  <span className="label">Role</span>
                  <p>{selectedAccount.contact_role ?? 'Not provided'}</p>
                </div>
                <div className="wide">
                  <span className="label">Description</span>
                  <p>{selectedAccount.description ?? 'Not provided'}</p>
                </div>
                <div className="wide">
                  <span className="label">Signal</span>
                  <p>{selectedAccount.signal ?? 'Not provided'}</p>
                </div>
                <div className="wide">
                  <span className="label">Objective</span>
                  <p>{selectedAccount.objective ?? 'Not provided'}</p>
                </div>
              </div>
              </div>
            ) : (
              <p className="empty-state">Load an account list to start.</p>
            )}
          </article>

          <article className={`card panel section-card ${outreach ? 'output-card-fade-in' : ''}`}>
            <div className="section-header">
              <div>
                <p className="card-kicker">Outreach</p>
                <h2>Generated outreach message</h2>
              </div>
            </div>
            {outreach ? (
              <>
                <div className="output-label-row">
                  <span className="output-label">Message preview</span>
                  <span className="output-note">Generated from account data and review-safe workflow rules.</span>
                </div>
                <div className="output-meta">
                  <span>Persona: {outreach.contact_role || 'Commercial lead'}</span>
                  <span>Channel: {outreach.channel}</span>
                  <span>Tone: {outreach.tone}</span>
                </div>
                <div className="callout">
                  <strong>Selected value props</strong>
                  <p>{joinList(outreach.selected_value_props)}</p>
                </div>
                <div className="callout">
                  <strong>Estimated impact</strong>
                  <p>{outreach.estimated_impact}</p>
                </div>
                <div className="message-card">
                  <div className="message-body">{renderMessagePreview(outreach.message)}</div>
                </div>
                {outreach.guardrail_flags.length > 0 ? (
                  <div className="flag-list">
                    {outreach.guardrail_flags.map((flag) => (
                      <span key={flag} className="flag">
                        {flag}
                      </span>
                    ))}
                  </div>
                ) : null}
              </>
            ) : (
              <p className="empty-state">Generate outreach for the selected account.</p>
            )}
          </article>

          <article className={`card panel section-card ${briefing ? 'output-card-fade-in' : ''}`}>
            <div className="section-header">
              <div>
                <p className="card-kicker">Briefing</p>
                <h2>Briefing note</h2>
              </div>
            </div>
            {briefing ? (
              <>
                <div className="briefing-summary">
                  <span className="output-label">Opportunity summary</span>
                  <p>{briefing.opportunity_summary}</p>
                </div>
                <div className="briefing-card markdown-card">
                  {renderBriefingMarkdown(briefing.briefing_markdown)}
                </div>
                {briefing.guardrail_flags.length > 0 ? (
                  <div className="flag-list">
                    {briefing.guardrail_flags.map((flag) => (
                      <span key={flag} className="flag">
                        {flag}
                      </span>
                    ))}
                  </div>
                ) : null}
              </>
            ) : (
              <p className="empty-state">Generate a briefing for the selected account.</p>
            )}
          </article>

          <article className="card panel section-card">
            <div className="section-header">
              <div>
                <p className="card-kicker">Queue</p>
                <h2>Mock outbound queue</h2>
              </div>
              <div className="section-header-actions">
                <div className="mini-stat">
                  <span>Queued items</span>
                  <strong>{queueSize}</strong>
                </div>
                <button type="button" className="secondary-button" onClick={clearLocalQueueView} disabled={queueSize === 0}>
                  Clear local view
                </button>
              </div>
            </div>
            <div className="quiet-note">Queued items are review-only drafts; no external delivery is triggered.</div>
            {queue.length > 0 ? (
              <div className="table-wrap queue-table">
                <table>
                  <thead>
                    <tr>
                      <th>Account</th>
                      <th>Persona</th>
                      <th>Channel</th>
                      <th>Status</th>
                      <th>Created</th>
                      <th>Day 3</th>
                      <th>Day 7</th>
                    </tr>
                  </thead>
                  <tbody>
                    {queue.map((item) => (
                      <tr key={item.queue_id}>
                        <td>{item.company_name}</td>
                        <td>{item.contact_role || 'Commercial lead'}</td>
                        <td>{item.channel}</td>
                        <td>{item.status}</td>
                        <td>{new Date(item.created_at).toLocaleString()}</td>
                        <td>{new Date(item.follow_up_day_3).toLocaleDateString()}</td>
                        <td>{new Date(item.follow_up_day_7).toLocaleDateString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="empty-state">No queued drafts yet. Add a draft to simulate the outbound review workflow.</p>
            )}
          </article>

          <article className="card panel section-card">
            <div className="section-header">
              <div>
                <p className="card-kicker">Exports</p>
                <h2>Generated export bundle</h2>
              </div>
            </div>
            {artifacts ? (
              <div className="export-bundle">
                <div className="export-success">
                  <strong>Export bundle ready for review.</strong>
                  <p>Exports are generated server-side for review and demo purposes.</p>
                </div>
                <ul className="artifact-list">
                  <li>
                    <span>Outreach CSV</span>
                    <code>outreach_examples.csv</code>
                  </li>
                  <li>
                    <span>Outreach JSON</span>
                    <code>outreach_examples.json</code>
                  </li>
                  <li>
                    <span>Briefing note 1</span>
                    <code>briefing_note_1.md</code>
                  </li>
                  <li>
                    <span>Briefing note 2</span>
                    <code>briefing_note_2.md</code>
                  </li>
                  <li>
                    <span>Queue export</span>
                    <code>send_queue.json</code>
                  </li>
                </ul>
              </div>
            ) : (
              <p className="empty-state">No exports generated yet. Run Export Examples to create demo artifacts.</p>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}
