import { Inbox } from 'lucide-react';

import { PageHeader } from '@/components/page-header';
import { TrendChart } from '@/components/reports/trend-chart';
import { Alert } from '@/components/ui/alert';
import { CountUp } from '@/components/ui/count-up';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { en } from '@/content/en';
import { getDashboard } from '@/lib/api/reports';
import {
  campaignStatusLabel,
  formatRate,
} from '@/lib/api/reports-types';

export default async function DashboardPage() {
  const data = await getDashboard();

  if (!data) {
    return (
      <>
        <PageHeader title={en.dashboard.title} description={en.dashboard.description} />
        <Alert variant="danger" title={en.dashboard.loadErrorTitle}>
          {en.dashboard.loadErrorBody}
        </Alert>
      </>
    );
  }

  const metrics = [
    {
      label: en.dashboard.activeCampaigns,
      value: String(data.active_campaigns),
      numericValue: data.active_campaigns,
      help: en.dashboard.activeCampaignsHelp,
    },
    {
      label: en.dashboard.emailsSent,
      value: String(data.delivered),
      numericValue: data.delivered,
      help: en.dashboard.deliveredHelp,
    },
    {
      label: en.dashboard.clickRate,
      value: data.has_data ? formatRate(data.click_rate) : en.dashboard.noValue,
      numericValue: undefined,
      help: en.dashboard.clickRateHelp,
    },
    {
      label: en.dashboard.reportRate,
      value: data.has_data ? formatRate(data.report_rate) : en.dashboard.noValue,
      numericValue: undefined,
      help: en.dashboard.reportRateHelp,
    },
  ];

  return (
    <>
      <PageHeader title={en.dashboard.title} description={en.dashboard.description} />

      <div className="space-y-6">
        <section aria-label={en.dashboard.title}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <Card key={metric.label} className="p-5 md:p-5" data-testid="dashboard-metric">
                <p className="text-sm font-medium text-muted-foreground">{metric.label}</p>
                <p className="mt-2 text-4xl font-bold leading-[44px] text-foreground">
                  {metric.numericValue !== undefined ? (
                    <CountUp value={metric.numericValue} />
                  ) : (
                    metric.value
                  )}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{metric.help}</p>
              </Card>
            ))}
          </div>
        </section>

        {!data.has_data ? (
          <Alert variant="info" title={en.dashboard.emptyTitle}>
            {en.dashboard.emptyBody}
          </Alert>
        ) : null}

        <Card>
          <CardHeader>
            <CardTitle>{en.dashboard.trendTitle}</CardTitle>
            <CardDescription>{en.dashboard.trendDescription}</CardDescription>
          </CardHeader>
          <CardContent>
            {data.trend.length > 0 ? (
              <TrendChart
                points={data.trend}
                title={en.dashboard.trendTitle}
                caption={en.dashboard.dashboardTableCaption}
              />
            ) : (
              <p className="text-sm text-muted-foreground">{en.dashboard.emptyBody}</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{en.dashboard.recentCampaigns}</CardTitle>
            <CardDescription>{en.dashboard.recentCampaignsDescription}</CardDescription>
          </CardHeader>
          <CardContent>
            {data.recent_campaigns.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border px-6 py-10 text-center">
                <span
                  className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-muted text-muted-foreground"
                  aria-hidden="true"
                >
                  <Inbox className="h-5 w-5" />
                </span>
                <p className="text-sm font-semibold text-foreground">{en.dashboard.emptyTitle}</p>
                <p className="max-w-md text-sm leading-6 text-muted-foreground">
                  {en.dashboard.recentCampaignsEmpty}
                </p>
              </div>
            ) : (
              <Table>
                <TableCaption>{en.dashboard.recentTableCaption}</TableCaption>
                <TableHeader>
                  <TableRow>
                    <TableHead scope="col">{en.dashboard.campaignColumn}</TableHead>
                    <TableHead scope="col">{en.dashboard.statusColumn}</TableHead>
                    <TableHead scope="col">{en.dashboard.groupColumn}</TableHead>
                    <TableHead scope="col">{en.dashboard.deliveredColumn}</TableHead>
                    <TableHead scope="col">{en.dashboard.clickRateColumn}</TableHead>
                    <TableHead scope="col">{en.dashboard.reportRateColumn}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.recent_campaigns.map((campaign) => (
                    <TableRow key={campaign.id}>
                      <TableCell className="font-medium">{campaign.name}</TableCell>
                      <TableCell>
                        <Badge variant="secondary">
                          {campaignStatusLabel(campaign.status)}
                        </Badge>
                      </TableCell>
                      <TableCell>{campaign.group_name ?? en.reports.noDepartment}</TableCell>
                      <TableCell>
                        {campaign.suppressed
                          ? en.dashboard.suppressed
                          : campaign.delivered}
                      </TableCell>
                      <TableCell>
                        {campaign.suppressed
                          ? en.dashboard.suppressed
                          : formatRate(campaign.click_rate)}
                      </TableCell>
                      <TableCell>
                        {campaign.suppressed
                          ? en.dashboard.suppressed
                          : formatRate(campaign.report_rate)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
