'use client';

import { useEffect, useRef, useState } from 'react';
import { Eye, EyeOff } from 'lucide-react';

import { en } from '@/content/en';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [reveal, setReveal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [errorCount, setErrorCount] = useState(0);
  const alertRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setHydrated(true);
  }, []);

  async function requestCsrfToken() {
    const res = await fetch('/api/v1/auth/csrf', {
      method: 'GET',
      cache: 'no-store',
      credentials: 'same-origin',
    });
    if (!res.ok) {
      throw new Error('csrf_unavailable');
    }
    const data = (await res.json()) as { csrf_token?: string };
    if (!data.csrf_token) {
      throw new Error('csrf_unavailable');
    }
    return data.csrf_token;
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (submitting) {
      return;
    }
    setErrorMessage('');
    setSubmitting(true);
    try {
      const token = await requestCsrfToken();
      const res = await fetch('/api/v1/auth/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRF-Token': token,
        },
        body: JSON.stringify({ email, password }),
      });
      if (res.ok) {
        window.location.href = '/';
        return;
      }
      if (res.status === 429) {
        const retryAfter = Number(res.headers.get('Retry-After')) || 60;
        setErrorMessage(
          en.auth.rateLimitMessage.replace('{seconds}', String(Math.max(retryAfter, 1)))
        );
      } else {
        setErrorMessage(en.auth.invalidCredentials);
      }
    } catch {
      setErrorMessage(en.auth.networkError);
    } finally {
      setErrorCount((c) => c + 1);
      setSubmitting(false);
    }
  }

  useEffect(() => {
    if (errorMessage !== '') {
      alertRef.current?.focus();
    }
  }, [errorMessage, errorCount]);

  return (
    <Card className="mx-auto w-full max-w-md">
      <CardHeader>
        <CardTitle>{en.app.name}</CardTitle>
        <CardDescription>{en.auth.loginPurpose}</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={onSubmit} noValidate>
          <div className="mb-4">
            <Label htmlFor="email">{en.auth.emailLabel}</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              autoFocus
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1"
              data-testid="login-email"
            />
          </div>
          <div className="mb-4">
            <Label htmlFor="password">{en.auth.passwordLabel}</Label>
            <div className="relative mt-1">
              <Input
                id="password"
                name="password"
                type={reveal ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pr-12"
                data-testid="login-password"
              />
              <Button
                type="button"
                variant="ghost"
                size="sm"
                className="absolute right-1 top-1/2 -translate-y-1/2 min-w-9 px-2"
                aria-label={reveal ? en.auth.hidePassword : en.auth.showPassword}
                aria-pressed={reveal}
                data-testid="login-reveal"
                onClick={() => setReveal((r) => !r)}
              >
                {reveal ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
              </Button>
            </div>
          </div>
          {errorMessage !== '' && (
            <Alert
              ref={alertRef}
              variant="danger"
              title={en.auth.genericErrorTitle}
              data-testid="login-error"
              className="mb-4 outline-none"
            >
              {errorMessage}
            </Alert>
          )}
          <Button
            type="submit"
            className="w-full"
            disabled={!hydrated || submitting}
            aria-busy={submitting}
            data-testid="login-submit"
          >
            {submitting ? en.auth.signInWorking : en.auth.signIn}
          </Button>
          <p className="mt-4 text-xs text-muted-foreground">{en.auth.authorizationNotice}</p>
        </form>
      </CardContent>
    </Card>
  );
}
