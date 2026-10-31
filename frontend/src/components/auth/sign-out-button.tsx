'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

import { en } from '@/content/en';
import { Button } from '@/components/ui/button';

export default function SignOutButton() {
  const [working, setWorking] = useState(false);
  const [hasError, setHasError] = useState(false);
  const router = useRouter();

  async function onSignOut() {
    setHasError(false);
    setWorking(true);
    try {
      const csrfRes = await fetch('/api/v1/auth/csrf', {
        method: 'GET',
        cache: 'no-store',
        credentials: 'same-origin',
      });
      if (!csrfRes.ok) {
        throw new Error('csrf_unavailable');
      }
      const csrfData = (await csrfRes.json()) as { csrf_token?: string };
      if (!csrfData.csrf_token) {
        throw new Error('csrf_unavailable');
      }
      const res = await fetch('/api/v1/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'X-CSRF-Token': csrfData.csrf_token },
      });
      if (!res.ok) {
        throw new Error('logout_failed');
      }
      router.push('/login');
      router.refresh();
    } catch {
      setHasError(true);
    } finally {
      setWorking(false);
    }
  }

  return (
    <div className="flex flex-col items-start gap-2">
      <Button
        variant="secondary"
        onClick={onSignOut}
        disabled={working}
        aria-busy={working}
        data-testid="sign-out"
      >
        {en.auth.signOut}
      </Button>
      {hasError && (
        <p role="alert" className="text-sm text-destructive">
          {en.auth.signOutError}
        </p>
      )}
    </div>
  );
}
