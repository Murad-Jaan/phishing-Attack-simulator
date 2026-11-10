import { Inbox } from 'lucide-react';

import { PageHeader } from '@/components/page-header';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { en } from '@/content/en';

const metrics = [
  { label: en.dashboard.activeCampaigns, value: en.dashboard.noValue },
  { label: en.dashboard.emailsSent, value: en.dashboard.noValue },
  { label: en.dashboard.clickRate, value: en.dashboard.noValue },
  { label: en.dashboard.reportRate, value: en.dashboard.noValue },
];

export default function DashboardPage() {
  return (
    <>
      <PageHeader title={en.dashboard.title} description={en.dashboard.description} />

      <div className="space-y-6">
        <section aria-label={en.dashboard.title}>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => (
              <Card key={metric.label} className="p-5 md:p-5">
                <p className="text-sm font-medium text-muted-foreground">{metric.label}</p>
                <p className="mt-2 text-4xl font-bold leading-[44px] text-foreground">
                  {metric.value}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">{en.dashboard.noData}</p>
              </Card>
            ))}
          </div>
        </section>

        <Card>
          <CardHeader>
            <CardTitle>{en.dashboard.recentCampaigns}</CardTitle>
            <CardDescription>{en.dashboard.recentCampaignsDescription}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-border px-6 py-10 text-center">
              <span
                className="flex h-10 w-10 items-center justify-center rounded-full bg-surface-muted text-muted-foreground"
                aria-hidden="true"
              >
                <Inbox className="h-5 w-5" />
              </span>
              <p className="text-sm font-semibold text-foreground">{en.dashboard.emptyTitle}</p>
              <p className="max-w-md text-sm leading-6 text-muted-foreground">
                {en.dashboard.emptyBody}
              </p>
            </div>
          </CardContent>
        </Card>
      </div>
    </>
  );
}
