import { notFound, redirect } from 'next/navigation';

import AuditLogWorkspace from '@/components/audit/audit-log-workspace';
import { PageHeader } from '@/components/page-header';
import { en } from '@/content/en';
import { getSessionUser } from '@/lib/auth/session';

export default async function AuditPage() {
  const user = await getSessionUser();
  if (!user) {
    redirect('/login');
  }
  if (user.role !== 'admin') {
    notFound();
  }

  return (
    <>
      <PageHeader title={en.audit.title} description={en.audit.description} />
      <AuditLogWorkspace />
    </>
  );
}
