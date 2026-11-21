import { AnalyzerWorkspace } from '@/components/analyzer/analyzer-workspace';
import { PageHeader } from '@/components/page-header';
import { en } from '@/content/en';

export default function AnalyzerPage() {
  return (
    <>
      <PageHeader title={en.analyzer.title} description={en.analyzer.description} />
      <AnalyzerWorkspace />
    </>
  );
}
