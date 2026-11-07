import { BarChart3 } from 'lucide-react';

import { PlaceholderPage } from '@/components/placeholder-page';
import { en } from '@/content/en';

export default function ReportsPage() {
  return (
    <PlaceholderPage
      title={en.nav.reports}
      description={en.pages.reports}
      icon={BarChart3}
    />
  );
}
