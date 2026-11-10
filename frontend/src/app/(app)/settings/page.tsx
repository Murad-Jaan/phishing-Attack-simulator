import { notFound, redirect } from 'next/navigation';

import { PageHeader } from '@/components/page-header';
import { Alert } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { en } from '@/content/en';
import { getOrganizationSettings } from '@/lib/api/settings';
import { getSessionUser } from '@/lib/auth/session';

export default async function SettingsPage() {
  const user = await getSessionUser();
  if (!user) {
    redirect('/login');
  }
  if (user.role !== 'admin') {
    notFound();
  }

  const settings = await getOrganizationSettings();

  return (
    <>
      <PageHeader title={en.settings.title} description={en.settings.description} />

      <Alert role="status" title={en.settings.readOnlyTitle} className="mb-6">
        {en.settings.readOnlyBody}
      </Alert>

      {settings ? (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>{en.settings.organizationProfile}</CardTitle>
              <CardDescription>{en.settings.organizationProfileDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">{en.settings.name}</dt>
                  <dd className="mt-1 text-sm font-semibold text-foreground">{settings.name}</dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    {en.settings.primaryDomain}
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-foreground">
                    {settings.primary_domain}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    {en.settings.timezone}
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-foreground">{settings.timezone}</dd>
                </div>
              </dl>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{en.settings.reportingDefaults}</CardTitle>
              <CardDescription>{en.settings.reportingDefaultsDescription}</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-4 sm:grid-cols-2">
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    {en.settings.retention}
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-foreground">
                    {settings.retention_days} {en.settings.days}
                  </dd>
                </div>
                <div>
                  <dt className="text-sm font-medium text-muted-foreground">
                    {en.settings.minGroupSize}
                  </dt>
                  <dd className="mt-1 text-sm font-semibold text-foreground">
                    {settings.min_group_size} {en.settings.people}
                  </dd>
                </div>
                <div className="sm:col-span-2">
                  <dt className="text-sm font-medium text-muted-foreground">
                    {en.settings.allowlist}
                  </dt>
                  <dd className="mt-2 flex flex-wrap gap-2">
                    {settings.send_domain_allowlist.length > 0 ? (
                      settings.send_domain_allowlist.map((domain) => (
                        <Badge key={domain} variant="outline">
                          {domain}
                        </Badge>
                      ))
                    ) : (
                      <span className="text-sm text-muted-foreground">
                        {en.settings.noAllowlist}
                      </span>
                    )}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>
      ) : (
        <Alert variant="danger" title={en.settings.loadErrorTitle}>
          {en.settings.loadErrorBody}
        </Alert>
      )}
    </>
  );
}
