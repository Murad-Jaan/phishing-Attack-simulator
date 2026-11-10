import { FileText } from 'lucide-react';

import { PlaceholderPage } from '@/components/placeholder-page';
import { en } from '@/content/en';

export default function TemplatesPage() {
  return (
    <PlaceholderPage
      title={en.nav.templates}
      description={en.pages.templates}
      icon={FileText}
    />
  );
}
