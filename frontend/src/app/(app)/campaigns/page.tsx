import { Send } from 'lucide-react';

import { PlaceholderPage } from '@/components/placeholder-page';
import { en } from '@/content/en';

export default function CampaignsPage() {
  return (
    <PlaceholderPage
      title={en.nav.campaigns}
      description={en.pages.campaigns}
      icon={Send}
    />
  );
}
