'use client';

import { useEffect, useState } from 'react';

import { GroupChart } from '@/components/reports/group-chart';
import { TrendChart } from '@/components/reports/trend-chart';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Label } from '@/components/ui/label';
import { SkeletonChart, SkeletonList } from '@/components/ui/skeleton';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { useToast } from '@/components/ui/toast';
import { en } from '@/content/en';
import {
  campaignStatusLabel,
  formatGeneratedAt,
  formatRate,
  type CampaignOption,
  type ReportData,
} from '@/lib/api/reports-types';

function format(template: string, values: Record<string, string | number>): string {
  return Object.entries(values).reduce(
    (result, [key, value]) => result.split(`{${key}}`).join(String(value)),
    template,
  );
}

async function getCsrfToken(): Promise<string> {
  const response = await fetch('/api/v1/auth/csrf', {
    method: 'GET',
    cache: 'no-store',
    credentials: 'same-origin',
  });
  if (!response.ok) {
    throw new Error('csrf_unavailable');
  }
  const data = (await response.json()) as { csrf_token?: string };
  if (!data.csrf_token) {
    throw new Error('csrf_unavailable');
  }
  return data.csrf_token;
}

export default function ReportsWorkspace() {
  const { showToast } = useToast();
  const [campaigns, setCampaigns] = useState<CampaignOption[]>([]);
  const [selected, setSelected] = useState('');
  const [data, setData] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState('');

  useEffect(() => {
    let active = true;
    async function loadCampaigns(): Promise<void> {
      try {
        const response = await fetch('/api/v1/reports/campaigns', {
          cache: 'no-store',
          credentials: 'same-origin',
        });
        if (!response.ok) {
          throw new Error('campaigns_unavailable');
        }
        const payload = (await response.json()) as { campaigns: CampaignOption[] };
        if (active) {
          setCampaigns(payload.campaigns);
        }
      } catch {
        if (active) {
          setError(en.reports.loadErrorBody);
        }
      }
    }
    void loadCampaigns();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    async function loadReport(): Promise<void> {
      setLoading(true);
      setError('');
      try {
        const query = selected ? `?campaign_id=${encodeURIComponent(selected)}` : '';
        const response = await fetch(`/api/v1/reports/summary${query}`, {
          cache: 'no-store',
          credentials: 'same-origin',
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error('report_unavailable');
        }
        const payload = (await response.json()) as ReportData;
        setData(payload);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        setData(null);
        setError(en.reports.loadErrorBody);
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }
    void loadReport();
    return () => controller.abort();
  }, [selected]);

  async function onExport(): Promise<void> {
    if (exporting) {
      return;
    }
    setExporting(true);
    setExportError('');
    try {
      const csrf = await getCsrfToken();
      const response = await fetch('/api/v1/reports/export', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': csrf,
        },
        body: JSON.stringify({ campaign_id: selected || null }),
      });
      if (!response.ok) {
        throw new Error('export_failed');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'campaign-report.csv';
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      showToast(en.reports.downloadToast);
    } catch {
      setExportError(en.reports.exportErrorBody);
      showToast(en.reports.exportErrorTitle, 'error');
    } finally {
      setExporting(false);
    }
  }

  const summary = data?.summary ?? null;
  const hasData = summary !== null && summary.delivered > 0;
  const selectedCampaign = campaigns.find((campaign) => campaign.id === selected);
  const suppressionCount = data?.suppressed_groups ?? 0;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{en.reports.filtersTitle}</CardTitle>
          <CardDescription>{en.reports.filtersDescription}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
            <div className="space-y-2">
              <Label htmlFor="report-campaign">{en.reports.campaignLabel}</Label>
              <select
                id="report-campaign"
                data-testid="reports-campaign"
                value={selected}
                onChange={(event) => setSelected(event.target.value)}
                className="flex min-h-11 w-full rounded-lg border border-input bg-surface px-3 py-2 text-base text-foreground shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background md:text-sm"
              >
                <option value="">{en.reports.allCampaigns}</option>
                {campaigns.map((campaign) => (
                  <option key={campaign.id} value={campaign.id}>
                    {campaign.name}
                    {campaign.suppressed ? ` (${en.reports.suppressedTitle})` : ''}
                  </option>
                ))}
              </select>
              {selectedCampaign ? (
                <p className="text-xs text-muted-foreground">
                  {campaignStatusLabel(selectedCampaign.status)}
                  {selectedCampaign.group_name ? ` · ${selectedCampaign.group_name}` : ''}
                </p>
              ) : null}
            </div>
            <Button
              type="button"
              variant="secondary"
              onClick={() => void onExport()}
              disabled={exporting || data === null}
              data-testid="reports-export"
            >
              {exporting ? en.reports.exporting : en.reports.exportCsv}
            </Button>
          </div>
          {data ? (
            <p className="text-xs text-muted-foreground">
              {format(en.reports.generatedAt, {
                time: formatGeneratedAt(data.generated_at),
              })}
              {' · '}
              {en.reports.minimumLabel}: {data.min_group_size}
              {suppressionCount > 0 ? (
                <>
                  {' · '}
                  {suppressionCount === 1
                    ? en.reports.suppressedGroupsOne
                    : format(en.reports.suppressedGroups, { count: suppressionCount })}
                </>
              ) : null}
            </p>
          ) : null}
        </CardContent>
      </Card>

      {error ? (
        <Alert variant="danger" title={en.reports.loadErrorTitle}>
          {error}
        </Alert>
      ) : null}
      {exportError ? (
        <Alert variant="danger" title={en.reports.exportErrorTitle}>
          {exportError}
        </Alert>
      ) : null}

      {loading ? (
        <Card aria-busy="true" data-testid="reports-loading">
          <CardHeader>
            <CardTitle>{en.reports.loading}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <SkeletonChart />
            <SkeletonList rows={3} />
          </CardContent>
        </Card>
      ) : null}

      {!loading && data?.suppressed ? (
        <Card data-testid="report-suppressed">
          <CardHeader>
            <CardTitle>{en.reports.suppressedTitle}</CardTitle>
            <CardDescription>
              {format(en.reports.suppressedBody, { minimum: data.min_group_size })}
            </CardDescription>
          </CardHeader>
        </Card>
      ) : null}

      {!loading && data && !data.suppressed && summary ? (
        <>
          {!hasData ? (
            <Alert variant="info" title={en.reports.emptyTitle}>
              {en.reports.emptyBody}
            </Alert>
          ) : null}

          <Card data-testid="report-funnel">
            <CardHeader>
              <CardTitle>{en.reports.funnelTitle}</CardTitle>
              <CardDescription>{en.reports.funnelDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {[
                  {
                    label: en.reports.delivered,
                    value: String(summary.delivered),
                    rate: null,
                    barRate: 1,
                  },
                  {
                    label: en.reports.clicked,
                    value: String(summary.clicked),
                    rate: summary.click_rate,
                    barRate: summary.click_rate,
                  },
                  {
                    label: en.reports.reported,
                    value: String(summary.reported),
                    rate: summary.report_rate,
                    barRate: summary.report_rate,
                  },
                  {
                    label: en.reports.quizCompleted,
                    value: String(summary.quiz_completed),
                    rate: summary.quiz_rate,
                    barRate: summary.quiz_rate,
                  },
                ].map((metric) => (
                  <div
                    key={metric.label}
                    className="rounded-xl border border-border bg-surface-muted p-4"
                  >
                    <p className="text-sm font-medium text-muted-foreground">
                      {metric.label}
                    </p>
                    <p className="mt-2 text-3xl font-bold leading-9 text-foreground">
                      {metric.value}
                    </p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {metric.rate === null
                        ? en.reports.rateOfDelivered
                        : formatRate(metric.rate)}
                    </p>
                    <svg
                      viewBox="0 0 100 8"
                      role="img"
                      aria-label={metric.label}
                      className="mt-3 h-2 w-full"
                    >
                      <rect width="100" height="8" rx="4" className="fill-current text-border" />
                      <rect
                        width={Math.max(0, Math.min(1, metric.barRate)) * 100}
                        height="8"
                        rx="4"
                        className="chart-bar fill-current text-primary"
                      />
                    </svg>
                  </div>
                ))}
              </div>
              <div className="mt-6">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead scope="col">{en.reports.funnelTitle}</TableHead>
                      <TableHead scope="col">{en.reports.countColumn}</TableHead>
                      <TableHead scope="col">{en.reports.rateColumn}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {[
                      {
                        label: en.reports.delivered,
                        count: summary.delivered,
                        rate: null,
                      },
                      {
                        label: en.reports.clicked,
                        count: summary.clicked,
                        rate: summary.click_rate,
                      },
                      {
                        label: en.reports.reported,
                        count: summary.reported,
                        rate: summary.report_rate,
                      },
                      {
                        label: en.reports.quizCompleted,
                        count: summary.quiz_completed,
                        rate: summary.quiz_rate,
                      },
                    ].map((row) => (
                      <TableRow key={row.label}>
                        <TableCell>{row.label}</TableCell>
                        <TableCell>{row.count}</TableCell>
                        <TableCell>
                          {row.rate === null
                            ? en.reports.rateOfDelivered
                            : formatRate(row.rate)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            </CardContent>
          </Card>

          <Card data-testid="report-groups">
            <CardHeader>
              <CardTitle>{en.reports.groupsTitle}</CardTitle>
              <CardDescription>{en.reports.groupsDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              {data.groups.length > 0 ? (
                <GroupChart groups={data.groups} caption={en.reports.groupsTableCaption} />
              ) : (
                <p className="text-sm text-muted-foreground">{en.reports.noGroups}</p>
              )}
            </CardContent>
          </Card>

          <Card data-testid="report-trend">
            <CardHeader>
              <CardTitle>{en.reports.trendTitle}</CardTitle>
              <CardDescription>{en.reports.trendDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              {data.trend.length > 0 ? (
                <TrendChart
                  points={data.trend}
                  title={en.reports.trendTitle}
                  caption={en.reports.trendTableCaption}
                />
              ) : (
                <p className="text-sm text-muted-foreground">{en.reports.emptyBody}</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{en.reports.definitionsTitle}</CardTitle>
              <CardDescription>{en.reports.definitionsDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 md:grid-cols-2">
                {[
                  [en.reports.delivered, en.reports.definitionDelivered],
                  [en.reports.clicked, en.reports.definitionClicked],
                  [en.reports.reported, en.reports.definitionReported],
                  [en.reports.quizCompleted, en.reports.definitionQuiz],
                  [
                    en.reports.suppressedTitle,
                    format(en.reports.definitionSuppression, {
                      minimum: data.min_group_size,
                    }),
                  ],
                ].map(([term, description]) => (
                  <div key={term}>
                    <dt className="text-sm font-semibold text-foreground">{term}</dt>
                    <dd className="mt-1 text-sm leading-6 text-muted-foreground">
                      {description}
                    </dd>
                  </div>
                ))}
              </dl>
            </CardContent>
          </Card>
        </>
      ) : null}
    </div>
  );
}
