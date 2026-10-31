import { redirect } from 'next/navigation';
import { ShieldCheck } from 'lucide-react';

import { en } from '@/content/en';
import SignOutButton from '@/components/auth/sign-out-button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { getSessionUser } from '@/lib/auth/session';

export default async function HomePage() {
  const user = await getSessionUser();
  if (!user) {
    redirect('/login');
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-8">
      <Card>
        <CardHeader>
          <CardTitle>{en.auth.signedInAs}</CardTitle>
          <CardDescription>
            {user.display_name} ({user.email})
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col items-start gap-6">
          <div className="flex items-center gap-2">
            <Badge variant="secondary">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              <span className="sr-only">{en.auth.roleLabel}: </span>
              {user.role}
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground max-w-prose">{en.auth.shellWelcome}</p>
          <SignOutButton />
        </CardContent>
      </Card>
    </div>
  );
}
