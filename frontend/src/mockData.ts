import type {
  AccountRecord,
  BriefingNote,
  BriefingRequest,
  Channel,
  ExportArtifacts,
  OutreachDraft,
  OutreachRequest,
  QueueItem,
  QueueOutreachRequest,
  QueueResponse,
  Tone
} from './types';

const sampleAccounts: AccountRecord[] = [
  {
    account_id: 'A-001',
    company_name: 'Northstar Leisure Group',
    category: 'family entertainment',
    sub_category: 'multi-site indoor entertainment',
    description: 'A multi-site leisure operator with growth plans and a near-term launch window.',
    hq_location: 'Manchester, UK',
    number_of_sites: 8,
    estimated_annual_visits: 1240000,
    estimated_average_ticket_price: 24.5,
    estimated_transaction_volume: 510000,
    estimated_annual_revenue: 30400000,
    region: 'UK North',
    contact_name: 'Avery Hughes',
    contact_role: 'Commercial Director',
    website: 'https://example.invalid/001',
    signal: 'new venue opening within the next quarter',
    objective: 'drive pre-opening bookings and memberships',
    notes: 'Values repeat visits and group revenue.',
    source: 'sample'
  },
  {
    account_id: 'A-002',
    company_name: 'Harbor Experience Co',
    category: 'immersive attraction',
    sub_category: 'single-site attraction',
    description: 'A destination attraction focused on retention and repeat visits.',
    hq_location: 'London, UK',
    number_of_sites: 1,
    estimated_annual_visits: 420000,
    estimated_average_ticket_price: 31,
    estimated_transaction_volume: 183000,
    estimated_annual_revenue: 13020000,
    region: 'Greater London',
    contact_name: 'Mina Patel',
    contact_role: 'Head of Growth',
    website: 'https://example.invalid/002',
    signal: 'loyalty and retention campaign is active',
    objective: 'increase repeat visits and off-peak demand',
    notes: 'Prefers concise messages with a clear commercial angle.',
    source: 'sample'
  },
  {
    account_id: 'A-003',
    company_name: 'Vertex Social Games',
    category: 'social gaming',
    sub_category: 'group entertainment venue',
    description: 'A group venue expanding its corporate events motion.',
    hq_location: 'Birmingham, UK',
    number_of_sites: 3,
    estimated_annual_visits: 280000,
    estimated_average_ticket_price: 27,
    estimated_transaction_volume: 119000,
    estimated_annual_revenue: 7560000,
    region: 'Midlands',
    contact_name: 'Jordan Price',
    contact_role: 'Revenue Lead',
    website: 'https://example.invalid/003',
    signal: 'corporate events team was recently expanded',
    objective: 'grow weekday group bookings',
    notes: 'Interested in practical ideas that can be launched quickly.',
    source: 'sample'
  },
  {
    account_id: 'A-004',
    company_name: 'Trailhead Adventure Co',
    category: 'active play',
    sub_category: 'regional leisure chain',
    description: 'A regional chain planning site expansion and yield improvements.',
    hq_location: 'Leeds, UK',
    number_of_sites: 5,
    estimated_annual_visits: 670000,
    estimated_average_ticket_price: 19.5,
    estimated_transaction_volume: 334000,
    estimated_annual_revenue: 13065000,
    region: 'Yorkshire',
    contact_name: 'Sophie Reed',
    contact_role: 'Operations Director',
    website: 'https://example.invalid/004',
    signal: 'site expansion planning is underway',
    objective: 'fill off-peak sessions and improve yield',
    notes: 'Sensitive to tone that feels too sales-heavy.',
    source: 'sample'
  }
];

const now = new Date('2026-04-26T12:00:00Z');

function formatMoney(value?: number | null): string {
  if (value === null || value === undefined) return 'Not provided';
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency: 'GBP',
    maximumFractionDigits: 0
  }).format(value);
}

function formatNumber(value?: number | null): string {
  if (value === null || value === undefined) return 'Not provided';
  return new Intl.NumberFormat('en-GB').format(value);
}

function formatCompactNumber(value?: number | null): string {
  if (value === null || value === undefined) return 'not provided';
  const amount = Math.abs(value);
  if (amount >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1).replace(/\.0$/, '')}m`;
  }
  if (amount >= 1_000) {
    return `${(value / 1_000).toFixed(1).replace(/\.0$/, '')}k`;
  }
  return `${value}`;
}

function formatCompactCurrency(value?: number | null): string {
  if (value === null || value === undefined) return 'not provided';
  const amount = Math.abs(value);
  if (amount >= 1_000_000) {
    return `$${(value / 1_000_000).toFixed(1).replace(/\.0$/, '')}m`;
  }
  if (amount >= 1_000) {
    return `$${(value / 1_000).toFixed(1).replace(/\.0$/, '')}k`;
  }
  return `$${value}`;
}

function toneOpening(tone: Tone): string {
  return {
    concise: 'Saw a few signals that made this worth a note.',
    warm: 'Noticed a few signals that felt relevant.',
    direct: 'Reaching out because this looks like a practical fit.'
  }[tone];
}

function openingSentence(account: AccountRecord, tone: Tone): string {
  const signal = (account.signal || '').toLowerCase();
  if (signal.includes('opening') || signal.includes('open')) {
    return {
      concise: `${account.company_name} is opening a new venue soon.`,
      warm: `${account.company_name} is opening a new venue soon, and the launch window looks worth a closer look.`,
      direct: `${account.company_name} is opening a new venue soon, so now is the right time to focus on launch demand.`
    }[tone];
  }
  if (signal.includes('retention')) {
    return {
      concise: `${account.company_name} is already running a retention campaign.`,
      warm: `${account.company_name} is already running a retention campaign, which makes repeat visits and off-peak demand the right focus.`,
      direct: `${account.company_name} is already running a retention campaign, so repeat visits and off-peak demand look like the right commercial angle.`
    }[tone];
  }
  if (signal.includes('corporate events')) {
    return {
      concise: `${account.company_name} has recently expanded its corporate events team.`,
      warm: `${account.company_name} has recently expanded its corporate events team, which puts weekday group bookings in focus.`,
      direct: `${account.company_name} has recently expanded its corporate events team, so weekday group bookings look like the immediate commercial angle.`
    }[tone];
  }
  return `${toneOpening(tone)} ${account.company_name} has a clear commercial opportunity.`;
}

function valueProps(account: AccountRecord): string[] {
  const props: string[] = [];
  if (account.number_of_sites) {
    const siteLabel = account.number_of_sites === 1 ? 'site' : 'sites';
    props.push(`Support commercial consistency across ${account.number_of_sites} ${siteLabel}`);
  }
  if (account.objective) {
    props.push(`Align the first conversation to the stated objective: ${account.objective}`);
  }
  if (account.signal) {
    props.push(`Use the current signal as a practical opening: ${account.signal}`);
  }
  if (!props.length && account.description) {
    props.push(`Reflect the operating model described in the account record: ${account.description}`);
  }
  if (!props.length) {
    props.push('Open a practical commercial conversation grounded in the account record');
  }
  return props.slice(0, 3);
}

function businessInsight(account: AccountRecord): string {
  const location = account.hq_location || account.region || "the account's market";
  if (account.number_of_sites && account.objective) {
    const sitePhrase = account.number_of_sites === 1 ? 'a single-site footprint' : `a ${account.number_of_sites}-site footprint`;
    return `${account.company_name} has ${sitePhrase} in ${location}, so the first message should stay focused on ${account.objective} and avoid broad feature claims.`;
  }
  if (account.signal) {
    return `${account.company_name} has a clear current signal in ${location}, so the outreach should stay tied to that trigger.`;
  }
  return `The account has enough commercial context to justify a short, practical first-touch message in ${location}.`;
}

function estimatedImpact(account: AccountRecord): string {
  const visits = account.estimated_annual_visits;
  const revenue = account.estimated_annual_revenue;
  if (visits && revenue) {
    const upliftVisits = Math.max(1, Math.round(visits * 0.05));
    const upliftRevenue = Math.max(1, Math.round(revenue * 0.05));
    return `A modest 5% uplift from the current base would be roughly ${formatNumber(upliftVisits)} additional annual visits or about ${formatMoney(upliftRevenue)}, depending on the lever.`;
  }
  if (revenue) {
    const upliftRevenue = Math.max(1, Math.round(revenue * 0.05));
    return `A modest 5% uplift could mean about ${formatMoney(upliftRevenue)}.`;
  }
  return 'A small uplift in conversion or repeat visits would likely justify a follow-up commercial conversation.';
}

function guardrails(account: AccountRecord, message: string, tone: Tone): string[] {
  const flags: string[] = ['Do not present unsupported claims as facts.', 'Keep the tone credible and non-salesy.', 'No real sending is performed from this prototype.'];
  if (message.split(/\s+/).length > 140) {
    flags.push('Message exceeds the 140-word limit.');
  }
  if (!account.contact_name) {
    flags.push('No named contact provided, so the greeting stays generic.');
  } else {
    flags.push('Named contact can be used only because it was present in the source file.');
  }
  if (!account.signal && !account.objective && !account.description) {
    flags.push('Source data is thin, so the message avoids unsupported claims.');
  }
  if (!['concise', 'warm', 'direct'].includes(tone)) {
    flags.push('Tone falls outside the supported set.');
  }
  return flags;
}

function composeMessage(account: AccountRecord, tone: Tone): string {
  const greeting = account.contact_name ? account.contact_name.split(/\s+/)[0] : 'there';
  const opening = openingSentence(account, tone);
  const focus = account.objective || 'the current commercial opportunity';
  const footprint = account.number_of_sites
    ? `${formatCompactNumber(account.number_of_sites)}-site footprint`
    : 'commercial footprint';
  const visits = account.estimated_annual_visits ? `roughly ${formatCompactNumber(account.estimated_annual_visits)} annual visits` : null;
  const volume = account.estimated_transaction_volume ? `an estimated ${formatCompactCurrency(account.estimated_transaction_volume)} transaction volume` : null;
  const ticket = account.estimated_average_ticket_price ? `about ${formatCompactCurrency(account.estimated_average_ticket_price)} average ticket` : null;
  const details = [visits, volume, ticket].filter(Boolean).join(', ');
  const firstLine = account.contact_name
    ? `Hi ${greeting}, ${account.company_name}'s ${footprint} and group-friendly format make ${focus} important.`
    : `${account.company_name}'s ${footprint} and group-friendly format make ${focus} important.`;
  const secondLine = details
    ? `With ${details}, even small improvements in conversion or upsell could be meaningful.`
    : `${opening} There is a clear case to keep the next step focused on one journey.`;
  const roleClause = account.contact_role
    ? ` For a ${account.contact_role}, the booking and group-sales journey looks like the right place to start.`
    : '';
  const closing = account.contact_role && /partnership/i.test(account.contact_role)
    ? 'Worth a quick look at where the booking and group-sales journey could be tightened?'
    : 'Worth a quick look at which journey could be tightened first?';
  const message = [
    firstLine,
    `${secondLine}${roleClause}`,
    closing
  ].join(' ');
  const words = message.split(/\s+/);
  return words.length > 100 ? words.slice(0, 100).join(' ') : message;
}

function personaForAccount(account: AccountRecord): string {
  if (account.contact_role) return account.contact_role;
  if (account.category) return `${account.category} lead`;
  return 'commercial lead';
}

function roleReasoning(account: AccountRecord): string {
  const parts = [account.category, account.sub_category, account.objective].filter(Boolean);
  return parts.length
    ? `The available record points to ${parts.join('; ')}.`
    : 'The record has enough commercial context to justify a practical first-touch message.';
}

function briefingMarkdown(account: AccountRecord, focus: BriefingRequest['focus'] = 'commercial', meetingPersona?: string | null): string {
  const overviewLines = [
    `${account.company_name} sits in the ${account.category || 'commercial'} space, with a sub-category of ${account.sub_category || 'unspecified sub-category'}.`,
    `The account is based in ${account.hq_location || account.region || 'an unspecified location'} and is represented here with ${account.number_of_sites ?? 'not provided'} site(s).`,
    `Estimated annual visits: ${formatNumber(account.estimated_annual_visits)}. Average ticket price: ${formatMoney(account.estimated_average_ticket_price)}. Estimated Easol annual revenue: ${formatMoney(account.estimated_annual_revenue)}.`
  ];
  if (account.description) {
    overviewLines.push(`Description from the source data: ${account.description.replace(/\.$/, '')}.`);
  }
  const persona = meetingPersona || account.contact_name || account.contact_role || personaForAccount(account);
  const roleLabel = account.contact_role || personaForAccount(account);
  const opportunitySummary = `For ${persona}, the clearest angle is to link ${account.signal || 'the current account profile'} to ${account.objective || 'a practical commercial next step'}. Focus the conversation on ${
    focus === 'operations'
      ? 'cost and complexity reduction, reporting consistency'
      : focus === 'growth'
        ? 'conversion improvement, average transaction value / upsell'
        : focus === 'customer_support'
          ? 'AI customer support, cost and complexity reduction'
          : 'conversion improvement, average transaction value / upsell'
  }.`;
  const quantified = [
    account.estimated_annual_visits && account.estimated_annual_revenue
      ? `25% conversion uplift value proposition: a meaningful improvement on one high-intent journey would be the upside case. Conservatively, a 5% visit uplift would be roughly ${formatNumber(Math.round(account.estimated_annual_visits * 0.05))} additional annual visits, and a 5% revenue uplift would be about ${formatMoney(Math.round(account.estimated_annual_revenue * 0.05))} in annual revenue. These are directional estimates based only on the account data.`
      : '25% conversion uplift value proposition: not enough data to calculate a directional estimate from the account record.',
    account.estimated_transaction_volume && account.estimated_average_ticket_price
      ? `Transaction volume context: a 5% uplift on ${formatMoney(account.estimated_transaction_volume)} would be about ${formatMoney(Math.round(account.estimated_transaction_volume * 0.05))} annually. This remains a directional estimate based only on the account data.`
      : account.estimated_average_ticket_price
        ? `Average ticket context: ${formatMoney(account.estimated_average_ticket_price)} per sale gives enough headroom to test upsell or conversion improvements without changing the core offer.`
        : 'Average ticket context: not enough pricing data to calculate a directional estimate.'
  ].join(' ');
  const talkingPoints = [
    `What is the current priority behind ${account.objective || 'the next commercial step'}?`,
    focus === 'customer_support'
      ? 'Where do customers need the most help today: booking, pre-visit questions, or post-visit support?'
      : focus === 'operations'
        ? 'Where do manual handoffs or reporting gaps create the most friction?'
        : 'Which part of the commercial funnel needs the most help: discovery, conversion, or repeat visits?',
    'Which enquiry, booking, or support step still needs manual follow-up?',
    'What would a small test need to prove before anyone would scale it?'
  ];
  const objections = [
    ['We already have a process for this.', 'Acknowledge the current process, then ask where the workflow still creates manual effort or lost conversion.'],
    ['Timing is not ideal.', 'Suggest a short, low-effort review instead of a full implementation discussion.'],
    ['We need to avoid adding complexity.', 'Position the conversation as one narrow test around a single journey, not a platform replacement.']
  ] as const;
  const systemsContext = 'Most teams in this space operate across separate ticketing, booking, CRM, support, spreadsheet, and reporting tools. The briefing should treat the opportunity as a way to connect those systems more cleanly, not replace everything at once.';
  const nextStep = 'Use the first call to choose one journey to inspect - for example group bookings, private hire, checkout conversion, or post-visit upsell - then agree whether a small workflow test is worth running.';

  return [
    `# Meeting Brief: ${account.company_name}`,
    '',
    '## 1. Company Overview',
    ...overviewLines.map((line) => `- ${line}`),
    '',
    '## 2. Individual / Persona Profile',
    account.contact_name && account.contact_role
      ? `For a ${roleLabel}, the primary contact is ${account.contact_name}.`
      : account.contact_name
        ? `Primary contact: ${account.contact_name}.`
        : account.contact_role
          ? `For a ${roleLabel}.`
          : `Likely persona: ${persona}.`,
    '',
    '## 3. Opportunity Analysis',
    opportunitySummary,
    '',
    '## 4. Quantified Value Case',
    quantified,
    '',
    '## 5. Suggested Talking Points',
    ...talkingPoints.map((line) => `- ${line}`),
    '',
    '## 6. Likely Objections',
    ...objections.flatMap(([objection, response]) => [`Objection: ${objection}`, `Response: ${response}`, '']),
    '',
    '## 7. Competitive / Systems Context',
    systemsContext,
    '',
    '## 8. Recommended Next Step',
    nextStep,
    ''
  ].join('\n');
}

function briefingGuardrails(account: AccountRecord, markdown: string): string[] {
  const flags: string[] = [];
  if (markdown.split(/\s+/).length > 1000) flags.push('Briefing note is longer than the requested maximum.');
  if (!account.contact_name) flags.push('No contact name was supplied, so the note is framed for the likely persona.');
  if (!account.contact_role) flags.push('No contact role was supplied, so the note avoids assuming a named job title.');
  if (!account.estimated_annual_visits && !account.estimated_annual_revenue && !account.estimated_transaction_volume) flags.push('Key scale data is missing, so the quantified value case is limited.');
  return flags;
}

export function getMockAccounts(): AccountRecord[] {
  return sampleAccounts;
}

export function generateMockOutreach(account: AccountRecord, request: OutreachRequest = { account_id: account.account_id }): OutreachDraft {
  const tone = request.tone ?? 'concise';
  const channel = request.channel ?? 'email';
  const message = composeMessage(account, tone);
  return {
    account_id: account.account_id,
    company_name: account.company_name,
    contact_name: account.contact_name,
    contact_role: account.contact_role,
    selected_value_props: valueProps(account),
    business_insight: businessInsight(account),
    estimated_impact: estimatedImpact(account),
    message,
    guardrail_flags: guardrails(account, message, tone),
    channel,
    tone
  };
}

export function generateMockBriefing(account: AccountRecord, request: BriefingRequest = { account_id: account.account_id }): BriefingNote {
  const markdown = briefingMarkdown(account, request.focus, request.meeting_persona);
  return {
    account_id: account.account_id,
    company_name: account.company_name,
    contact_name: account.contact_name,
    contact_role: account.contact_role,
    briefing_markdown: markdown,
    opportunity_summary: markdown.split('\n').find((line) => line.startsWith('For ')) || 'Practical account briefing.',
    quantified_value_case: markdown.split('## 4. Quantified Value Case')[1]?.split('## 5. Suggested Talking Points')[0]?.trim() || 'Not enough data.',
    talking_points: [
      `What is the current priority behind ${account.objective || 'the next commercial step'}?`,
      'Which enquiry, booking, or support step still needs manual follow-up?',
      'What would a small test need to prove before anyone would scale it?'
    ],
    likely_objections: ['We already have a process for this.', 'Timing is not ideal.', 'We need to avoid adding complexity.'],
    recommended_next_step: markdown.split('## 8. Recommended Next Step')[1]?.trim() || 'Propose a short follow-up.',
    guardrail_flags: briefingGuardrails(account, markdown)
  };
}

export function enqueueMockOutreach(account: AccountRecord, request: QueueOutreachRequest = { account_id: account.account_id }): QueueItem {
  const outreach = generateMockOutreach(account, request);
  const createdAt = now.toISOString();
  return {
    queue_id: `QUEUE-${account.account_id}`,
    account_id: account.account_id,
    company_name: account.company_name,
    contact_name: account.contact_name,
    contact_role: account.contact_role,
    channel: request.channel ?? 'email',
    message: outreach.message,
    selected_value_props: outreach.selected_value_props,
    status: 'pending_review',
    created_at: createdAt,
    follow_up_day_3: new Date(now.getTime() + 3 * 24 * 60 * 60 * 1000).toISOString(),
    follow_up_day_7: new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000).toISOString(),
    guardrail_flags: outreach.guardrail_flags
  };
}

export function buildMockQueue(accounts: AccountRecord[]): QueueResponse {
  const items = accounts.slice(0, 2).map((account) => enqueueMockOutreach(account));
  return { items, queue_size: items.length };
}

export function buildMockArtifacts(): ExportArtifacts {
  return {
    outreach_csv_path: 'outputs/outreach_examples.csv',
    outreach_json_path: 'outputs/outreach_examples.json',
    briefing_note_1_path: 'outputs/briefing_note_1.md',
    briefing_note_2_path: 'outputs/briefing_note_2.md',
    send_queue_path: 'outputs/send_queue.json'
  };
}

export function buildMockExport(account: AccountRecord): { outreach: OutreachDraft; briefing: BriefingNote; queueItem: QueueItem; artifacts: ExportArtifacts } {
  const outreach = generateMockOutreach(account);
  const briefing = generateMockBriefing(account);
  const queueItem = enqueueMockOutreach(account);
  return { outreach, briefing, queueItem, artifacts: buildMockArtifacts() };
}
