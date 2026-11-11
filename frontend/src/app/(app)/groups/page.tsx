import { redirect } from 'next/navigation';

import GroupsWorkspace from '@/components/groups/groups-workspace';
import { getSessionUser } from '@/lib/auth/session';

export default async function GroupsOverviewPage() {
  const user = await getSessionUser();
  if (!user) {
    redirect('/login');
  }

  return <GroupsWorkspace />;
}
