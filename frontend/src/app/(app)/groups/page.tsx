import { Users } from 'lucide-react';

import { PlaceholderPage } from '@/components/placeholder-page';
import { en } from '@/content/en';

export default function GroupsPage() {
  return (
    <PlaceholderPage title={en.nav.groups} description={en.pages.groups} icon={Users} />
  );
}
