import { redirect } from 'next/navigation';

import CampaignsWorkspace from '@/components/campaigns/campaigns-workspace';
import { getSessionUser } from '@/lib/auth/session';

export default async function CampaignsPage() {
  const user = await getSessionUser();
  if (!user) {
    redirect('/login');
  }

  return <CampaignsWorkspace isAdmin={user.role === 'admin'} />;
}
