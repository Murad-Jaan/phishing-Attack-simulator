import Link from 'next/link';
import { redirect } from 'next/navigation';
import { UserPlus } from 'lucide-react';

import { en } from '@/content/en';
import ThemeToggle from '@/components/theme-toggle';
import { buttonVariants } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getSessionUser } from '@/lib/auth/session';
import { getStoredTheme } from '@/lib/theme-server';

export default async function SignUpPage() {
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
        <Card className="auth-card mx-auto w-full max-w-md">
          <CardHeader className="mb-6 items-center text-center">
            <span className="auth-shield flex h-12 w-12 items-center justify-center rounded-xl">
              <UserPlus className="h-6 w-6" aria-hidden="true" />
            </span>
            <p className="mt-1 text-sm font-semibold text-foreground">{en.app.name}</p>
            <CardTitle as="h1" className="mt-2 text-2xl font-bold leading-8">
              {en.auth.signUpTitle}
            </CardTitle>
            <CardDescription>{en.auth.signUpBody}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-6 text-muted-foreground">{en.auth.signUpNote}</p>
            <Link href="/login" className={buttonVariants({ className: 'w-full' })}>
              {en.auth.backToSignIn}
            </Link>
          </CardContent>
        </Card>
      </main>
    </div>
  );
}
