export type Channel = 'email' | 'linkedin';
export type Tone = 'concise' | 'warm' | 'direct';
export type BriefingFocus = 'commercial' | 'operations' | 'growth' | 'customer_support';

export interface AccountRecord {
  account_id: string;
  company_name: string;
  category?: string | null;
  sub_category?: string | null;
  description?: string | null;
  hq_location?: string | null;
  number_of_sites?: number | null;
  estimated_annual_visits?: number | null;
  estimated_average_ticket_price?: number | null;
  estimated_transaction_volume?: number | null;
  estimated_annual_revenue?: number | null;
  region?: string | null;
  contact_name?: string | null;
  contact_role?: string | null;
  website?: string | null;
  signal?: string | null;
  objective?: string | null;
  notes?: string | null;
  source?: string | null;
}

export interface OutreachRequest {
  account_id: string;
  channel?: Channel;
  tone?: Tone;
}

export interface BriefingRequest {
  account_id: string;
  meeting_persona?: string | null;
  focus?: BriefingFocus;
}

export interface QueueOutreachRequest {
  account_id: string;
  channel?: Channel;
  tone?: Tone;
}

export interface OutreachDraft {
  account_id: string;
  company_name: string;
  contact_name?: string | null;
  contact_role?: string | null;
  selected_value_props: string[];
  business_insight: string;
  estimated_impact: string;
  message: string;
  guardrail_flags: string[];
  channel: Channel;
  tone: Tone;
}

export interface BriefingNote {
  account_id: string;
  company_name: string;
  contact_name?: string | null;
  contact_role?: string | null;
  briefing_markdown: string;
  opportunity_summary: string;
  quantified_value_case: string;
  talking_points: string[];
  likely_objections: string[];
  recommended_next_step: string;
  guardrail_flags: string[];
}

export interface QueueItem {
  queue_id: string;
  account_id: string;
  company_name: string;
  contact_name?: string | null;
  contact_role?: string | null;
  channel: Channel;
  message: string;
  selected_value_props: string[];
  status: string;
  created_at: string;
  follow_up_day_3: string;
  follow_up_day_7: string;
  guardrail_flags: string[];
}

export interface QueueResponse {
  items: QueueItem[];
  queue_size: number;
}

export interface DataSourceInfo {
  data_source: 'google_sheet' | 'local_file' | 'sample_fallback';
  data_source_detail: string;
  data_load_warning?: string | null;
  loaded_accounts: number;
}

export interface ExportArtifacts {
  outreach_csv_path: string;
  outreach_json_path: string;
  briefing_note_1_path: string;
  briefing_note_2_path: string;
  send_queue_path: string;
}

export interface QueueResult {
  item: QueueItem;
  queue_size: number;
}

export interface ExportExamplesResponse {
  outreach: OutreachDraft[];
  briefings: BriefingNote[];
  artifacts: ExportArtifacts;
}
