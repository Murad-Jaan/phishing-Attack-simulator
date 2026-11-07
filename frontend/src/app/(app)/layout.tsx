import type { ReactNode } from 'react';
import { redirect } from 'next/navigation';

import { AppShell } from '@/components/app-shell';
import { getSessionUser } from '@/lib/auth/session';
import { getStoredTheme } from '@/lib/theme-server';

export default async function AppLayout({ children }: { children: ReactNode }) {
  const [user, theme] = await Promise.all([getSessionUser(), getStoredTheme()]);

  if (!user) {
    redirect('/login');
  }

  return (
    <AppShell user={user} initialTheme={theme}>
      {children}
    </AppShell>
  );
}
