import { en } from '@/content/en';

export interface CampaignOption {
  id: string;
  name: string;
  status: string;
  group_id: string | null;
  group_name: string | null;
  member_count: number | null;
  suppressed: boolean;
}

export interface ReportSummary {
  delivered: number;
  clicked: number;
  reported: number;
  quiz_completed: number;
  click_rate: number;
  report_rate: number;
  quiz_rate: number;
}

export interface ReportScope {
  campaign_id: string | null;
  campaign_name: string;
  group_id: string | null;
  group_name: string | null;
}

export interface GroupReport {
  id: string;
  name: string;
  department: string | null;
  delivered: number;
  clicked: number;
  reported: number;
  quiz_completed: number;
  click_rate: number;
  report_rate: number;
  quiz_rate: number;
}

export interface TrendPoint {
  date: string;
  delivered: number;
  clicked: number;
  reported: number;
  quiz_completed: number;
  click_rate: number;
  report_rate: number;
}

export interface ReportData {
  generated_at: string;
  scope: ReportScope;
  min_group_size: number;
  suppressed: boolean;
  suppressed_groups: number;
  summary: ReportSummary | null;
  groups: GroupReport[];
  trend: TrendPoint[];
}

export interface RecentCampaign {
  id: string;
  name: string;
  status: string;
  group_name: string | null;
  delivered: number | null;
  click_rate: number | null;
  report_rate: number | null;
  suppressed: boolean;
}

export interface DashboardData {
  generated_at: string;
  active_campaigns: number;
  delivered: number;
  click_rate: number;
  report_rate: number;
  quiz_rate: number;
  has_data: boolean;
  min_group_size: number;
  suppressed_groups: number;
  trend: TrendPoint[];
  recent_campaigns: RecentCampaign[];
}

export const campaignStatusLabels: Record<string, string> = {
  draft: en.campaigns.statusDraft,
  pending_authorization: en.campaigns.statusPendingAuthorization,
  approved: en.campaigns.statusApproved,
  scheduled: en.campaigns.statusScheduled,
  running: en.campaigns.statusRunning,
  paused: en.campaigns.statusPaused,
  completed: en.campaigns.statusCompleted,
  cancelled: en.campaigns.statusCancelled,
};

export function campaignStatusLabel(status: string): string {
  return campaignStatusLabels[status] ?? status;
}

export function formatRate(value: number | null | undefined): string {
  if (value == null || Number.isNaN(value)) {
    return en.dashboard.noValue;
  }
  return `${Math.round(value * 100)}%`;
}

export function formatDay(value: string): string {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('en', {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  }).format(date);
}

export function formatGeneratedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat('en', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date);
}
