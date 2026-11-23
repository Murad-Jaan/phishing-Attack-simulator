import { redirect } from 'next/navigation';

import LoginForm from '@/components/auth/login-form';
import ThemeToggle from '@/components/theme-toggle';
import { getSessionUser } from '@/lib/auth/session';
import { getStoredTheme } from '@/lib/theme-server';

export default async function LoginPage() {
  const [user, theme] = await Promise.all([getSessionUser(), getStoredTheme()]);

  if (user) {
    redirect('/');
  }

  return (
    <div className="page-transition relative isolate flex min-h-dvh flex-col overflow-hidden bg-background">
      <div className="aurora-backdrop" aria-hidden="true">
        <span className="aurora-blob aurora-blob-a" />
        <span className="aurora-blob aurora-blob-b" />
        <span className="aurora-blob aurora-blob-c" />
        <div className="aurora-grid" />
      </div>
      <div className="relative z-10 flex justify-end px-4 py-4">
        <ThemeToggle initialTheme={theme} />
      </div>
      <main
        id="main-content"
        tabIndex={-1}
        className="relative z-10 flex flex-1 items-center justify-center px-4 pb-12"
      >
        <LoginForm />
      </main>
    </div>
  );
}
