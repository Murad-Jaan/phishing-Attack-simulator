import { MailSearch } from 'lucide-react';

import { PlaceholderPage } from '@/components/placeholder-page';
import { en } from '@/content/en';

export default function AnalyzerPage() {
  return (
    <PlaceholderPage
      title={en.nav.analyzer}
      description={en.pages.analyzer}
      icon={MailSearch}
    />
  );
}
