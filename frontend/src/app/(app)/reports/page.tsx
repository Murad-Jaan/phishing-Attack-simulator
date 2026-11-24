import { PageHeader } from '@/components/page-header';
import ReportsWorkspace from '@/components/reports/reports-workspace';
import { en } from '@/content/en';

export default function ReportsPage() {
  return (
    <>
      <PageHeader title={en.reports.title} description={en.reports.description} />
      <ReportsWorkspace />
    </>
  );
}
