import { PageHeader } from '@/components/page-header';
import { TemplateLibrary } from '@/components/templates/template-library';
import { en } from '@/content/en';

export default function TemplatesPage() {
  return (
    <>
      <PageHeader title={en.templates.title} description={en.templates.description} />
      <TemplateLibrary />
    </>
  );
}
