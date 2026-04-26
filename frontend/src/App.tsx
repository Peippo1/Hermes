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
  exportExamples,
  fetchAccounts,
  fetchQueue,
  generateBriefing,
  generateOutreach,
  hasApiBaseUrl,
  queueOutreach
} from './api';
import type { AccountRecord, BriefingNote, ExportArtifacts, OutreachDraft, QueueItem, QueueResponse, Tone } from './types';

type Mode = 'api' | 'mock';
type Status = 'idle' | 'loading' | 'ready' | 'error';

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

function joinList(values: string[] | undefined): string {
  return values && values.length > 0 ? values.join(' • ') : 'None';
}

export default function App() {
  const [mode, setMode] = useState<Mode>('mock');
  const [status, setStatus] = useState<Status>('idle');
  const [statusMessage, setStatusMessage] = useState<string>('Loading account data.');
  const [accounts, setAccounts] = useState<AccountRecord[]>([]);
  const [selectedAccountId, setSelectedAccountId] = useState<string>('');
  const [outreach, setOutreach] = useState<OutreachDraft | null>(null);
  const [briefing, setBriefing] = useState<BriefingNote | null>(null);
  const [queue, setQueue] = useState<QueueItem[]>([]);
  const [queueSize, setQueueSize] = useState<number>(0);
  const [artifacts, setArtifacts] = useState<ExportArtifacts | null>(null);

  const selectedAccount = useMemo(
    () => accounts.find((account) => account.account_id === selectedAccountId) ?? null,
    [accounts, selectedAccountId]
  );

  useEffect(() => {
    let cancelled = false;
    async function loadAccounts() {
      if (!hasApiBaseUrl()) {
        const mockAccounts = getMockAccounts();
        const mockQueue = buildMockQueue(mockAccounts);
        if (cancelled) return;
        setMode('mock');
        setStatus('ready');
        setStatusMessage('Demo mock mode is active.');
        setAccounts(mockAccounts);
        setSelectedAccountId(mockAccounts[0]?.account_id ?? '');
        setQueue(mockQueue.items);
        setQueueSize(mockQueue.queue_size);
        return;
      }
      setStatus('loading');
      try {
        const remoteAccounts = await fetchAccounts();
        if (cancelled) return;
        setMode('api');
        setStatus('ready');
        setStatusMessage('Connected to the backend.');
        setAccounts(remoteAccounts);
        setSelectedAccountId(remoteAccounts[0]?.account_id ?? '');
      } catch {
        if (cancelled) return;
        const mockAccounts = getMockAccounts();
      setMode('mock');
      setStatus('ready');
      setStatusMessage('Demo mock mode is active.');
      setAccounts(mockAccounts);
      setSelectedAccountId(mockAccounts[0]?.account_id ?? '');
      const mockQueue = buildMockQueue(mockAccounts);
      setQueue(mockQueue.items);
      setQueueSize(mockQueue.queue_size);
      }
    }

    loadAccounts();
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleGenerateOutreach() {
    if (!selectedAccount) return;
    if (mode === 'mock') {
      setOutreach(generateMockOutreach(selectedAccount));
      return;
    }
    try {
      setOutreach(await generateOutreach({ account_id: selectedAccount.account_id }));
    } catch {
      setMode('mock');
      setStatusMessage('Demo mock mode is active.');
      setOutreach(generateMockOutreach(selectedAccount));
    }
  }

  async function handleGenerateBriefing() {
    if (!selectedAccount) return;
    if (mode === 'mock') {
      setBriefing(generateMockBriefing(selectedAccount));
      return;
    }
    try {
      setBriefing(await generateBriefing({ account_id: selectedAccount.account_id }));
    } catch {
      setMode('mock');
      setStatusMessage('Demo mock mode is active.');
      setBriefing(generateMockBriefing(selectedAccount));
    }
  }

  async function handleQueueOutreach() {
    if (!selectedAccount) return;
    if (mode === 'mock') {
      const item = enqueueMockOutreach(selectedAccount);
      setQueue((current) => [item, ...current.filter((entry) => entry.account_id !== item.account_id)]);
      setQueueSize((current) => current + 1);
      if (!outreach) setOutreach(generateMockOutreach(selectedAccount));
      return;
    }
    try {
      const response = await queueOutreach({ account_id: selectedAccount.account_id });
      setQueue((current) => [response.item, ...current.filter((entry) => entry.queue_id !== response.item.queue_id)]);
      setQueueSize(response.queue_size);
      if (!outreach) {
        setOutreach(await generateOutreach({ account_id: selectedAccount.account_id }));
      }
    } catch {
      setMode('mock');
      setStatusMessage('Demo mock mode is active.');
      const item = enqueueMockOutreach(selectedAccount);
      setQueue((current) => [item, ...current]);
      setQueueSize((current) => current + 1);
      if (!outreach) setOutreach(generateMockOutreach(selectedAccount));
    }
  }

  async function handleViewQueue() {
    if (mode === 'mock') {
      const response = buildMockQueue(accounts);
      setQueue(response.items);
      setQueueSize(response.queue_size);
      return;
    }
    try {
      const response = await fetchQueue();
      setQueue(response.items);
      setQueueSize(response.queue_size);
    } catch {
      setMode('mock');
      setStatusMessage('Demo mock mode is active.');
      const response = buildMockQueue(accounts);
      setQueue(response.items);
      setQueueSize(response.queue_size);
    }
  }

  async function handleExportExamples() {
    if (mode === 'mock') {
      if (!selectedAccount) return;
      const exportBundle = buildMockExport(selectedAccount);
      setOutreach(exportBundle.outreach);
      setBriefing(exportBundle.briefing);
      setQueue((current) => [exportBundle.queueItem, ...current]);
      setArtifacts(buildMockArtifacts());
      return;
    }
    try {
      const response = await exportExamples();
      setOutreach(response.outreach[0] ?? null);
      setBriefing(response.briefings[0] ?? null);
      setArtifacts(response.artifacts);
    } catch {
      setMode('mock');
      setStatusMessage('Demo mock mode is active.');
      if (!selectedAccount) return;
      const exportBundle = buildMockExport(selectedAccount);
      setOutreach(exportBundle.outreach);
      setBriefing(exportBundle.briefing);
      setQueue((current) => [exportBundle.queueItem, ...current]);
      setArtifacts(buildMockArtifacts());
    }
  }

  return (
    <div className="shell">
      <main className="app-shell">
        <header className="hero">
          <div className="hero-copy">
            <div className="eyebrow-row">
              <span className={`badge ${mode === 'mock' ? 'badge-warning' : 'badge-success'}`}>
                {mode === 'mock' ? 'Demo mock mode' : 'Connected mode'}
              </span>
              <span className="status-chip">{status === 'loading' ? 'Loading' : statusMessage}</span>
            </div>
            <h1>Hermes — AI Sales Enablement Workflow Prototype</h1>
            <p className="subheading">
              Account list → personalised outreach → meeting briefing → mock outbound queue
            </p>
          </div>
          <div className="hero-metric">
            <div className="metric-label">Selected account</div>
            <div className="metric-value">{selectedAccount?.company_name ?? 'No account selected'}</div>
            <div className="metric-subtle">{selectedAccount?.category ?? 'Choose an account to begin'}</div>
          </div>
        </header>

        <section className="control-bar card">
          <div className="field">
            <label htmlFor="account">Account selector</label>
            <select
              id="account"
              value={selectedAccountId}
              onChange={(event) => setSelectedAccountId(event.target.value)}
            >
              {accounts.map((account) => (
                <option key={account.account_id} value={account.account_id}>
                  {account.company_name}
                </option>
              ))}
            </select>
          </div>
          <div className="button-row">
            <button type="button" onClick={handleGenerateOutreach}>Generate Outreach</button>
            <button type="button" onClick={handleGenerateBriefing}>Generate Briefing</button>
            <button type="button" onClick={handleQueueOutreach}>Add to Mock Queue</button>
            <button type="button" onClick={handleViewQueue}>View Queue</button>
            <button type="button" onClick={handleExportExamples}>Export Examples</button>
          </div>
        </section>

        <section className="grid">
          <article className="card preview-card">
            <div className="card-header">
              <div>
                <p className="card-kicker">Account preview</p>
                <h2>{selectedAccount?.company_name ?? 'Select an account'}</h2>
              </div>
              <div className="mini-stat">
                <span>Region</span>
                <strong>{selectedAccount?.region ?? 'Not provided'}</strong>
              </div>
            </div>

            {selectedAccount ? (
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
                  <span className="label">Average ticket</span>
                  <p>{formatMoney(selectedAccount.estimated_average_ticket_price)}</p>
                </div>
                <div>
                  <span className="label">Annual revenue</span>
                  <p>{formatMoney(selectedAccount.estimated_annual_revenue)}</p>
                </div>
                <div>
                  <span className="label">Contact</span>
                  <p>{selectedAccount.contact_name ?? 'Not provided'}</p>
                </div>
                <div>
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
            ) : (
              <p className="empty-state">Load an account list to start.</p>
            )}
          </article>

          <article className="card output-card">
            <div className="card-header">
              <div>
                <p className="card-kicker">Outreach</p>
                <h2>Generated outreach message</h2>
              </div>
            </div>
            {outreach ? (
              <>
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
                  <pre>{outreach.message}</pre>
                </div>
                <div className="flag-list">
                  {outreach.guardrail_flags.map((flag) => (
                    <span key={flag} className="flag">{flag}</span>
                  ))}
                </div>
              </>
            ) : (
              <p className="empty-state">Generate outreach for the selected account.</p>
            )}
          </article>

          <article className="card output-card">
            <div className="card-header">
              <div>
                <p className="card-kicker">Briefing</p>
                <h2>Briefing markdown</h2>
              </div>
            </div>
            {briefing ? (
              <>
                <div className="output-meta">
                  <span>Opportunity summary: {briefing.opportunity_summary}</span>
                </div>
                <div className="markdown-card">
                  <pre>{briefing.briefing_markdown}</pre>
                </div>
                <div className="flag-list">
                  {briefing.guardrail_flags.map((flag) => (
                    <span key={flag} className="flag">{flag}</span>
                  ))}
                </div>
              </>
            ) : (
              <p className="empty-state">Generate a briefing for the selected account.</p>
            )}
          </article>

          <article className="card output-card">
            <div className="card-header">
              <div>
                <p className="card-kicker">Queue</p>
                <h2>Mock outbound queue</h2>
              </div>
              <div className="mini-stat">
                <span>Queued items</span>
                <strong>{queueSize}</strong>
              </div>
            </div>
            {queue.length > 0 ? (
              <div className="table-wrap">
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
              <p className="empty-state">Add a draft to the mock queue to show review state.</p>
            )}
          </article>

          <article className="card output-card">
            <div className="card-header">
              <div>
                <p className="card-kicker">Exports</p>
                <h2>Artifact paths</h2>
              </div>
            </div>
            {artifacts ? (
              <ul className="artifact-list">
                <li><code>{artifacts.outreach_csv_path}</code></li>
                <li><code>{artifacts.outreach_json_path}</code></li>
                <li><code>{artifacts.briefing_note_1_path}</code></li>
                <li><code>{artifacts.briefing_note_2_path}</code></li>
                <li><code>{artifacts.send_queue_path}</code></li>
              </ul>
            ) : (
              <p className="empty-state">Export examples to display artifact paths.</p>
            )}
          </article>
        </section>
      </main>
    </div>
  );
}
