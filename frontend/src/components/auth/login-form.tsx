'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { Eye, EyeOff, ShieldCheck } from 'lucide-react';

import { en } from '@/content/en';
import { Alert } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { PASSWORD_RESET_ENABLED } from '@/lib/features';

export default function LoginForm() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [reveal, setReveal] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [hydrated, setHydrated] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [invalidCredentials, setInvalidCredentials] = useState(false);
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
    setInvalidCredentials(false);
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
          en.auth.rateLimitMessage.replace('{seconds}', String(Math.max(retryAfter, 1))),
        );
      } else {
        setInvalidCredentials(true);
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

  const errorDescribedBy = errorMessage !== '' ? 'login-error' : undefined;

  return (
    <Card className="mx-auto w-full max-w-md">
      <CardHeader className="mb-6 items-center text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary text-primary-foreground">
          <ShieldCheck className="h-6 w-6" aria-hidden="true" />
        </span>
        <p className="mt-1 text-sm font-semibold text-foreground">{en.app.name}</p>
        <CardTitle as="h1" className="mt-2 text-2xl font-bold leading-8">
          {en.auth.welcomeTitle}
        </CardTitle>
        <CardDescription>{en.auth.loginPurpose}</CardDescription>
      </CardHeader>
      <CardContent>
        {errorMessage !== '' && (
          <Alert
            ref={alertRef}
            id="login-error"
            variant="danger"
            title={en.auth.genericErrorTitle}
            data-testid="login-error"
            tabIndex={-1}
            className="mb-4 outline-none"
          >
            {errorMessage}
          </Alert>
        )}
        <form onSubmit={onSubmit} noValidate className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">{en.auth.emailLabel}</Label>
            <Input
              id="email"
              name="email"
              type="email"
              autoComplete="email"
              autoFocus
              required
              placeholder={en.auth.emailPlaceholder}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              aria-invalid={invalidCredentials || undefined}
              aria-describedby={errorDescribedBy}
              data-testid="login-email"
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <Label htmlFor="password">{en.auth.passwordLabel}</Label>
              {PASSWORD_RESET_ENABLED && (
                <Link
                  href="/forgot-password"
                  className="rounded text-sm font-semibold text-primary underline-offset-4 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-surface"
                >
                  {en.auth.forgotPassword}
                </Link>
              )}
            </div>
            <div className="relative">
              <Input
                id="password"
                name="password"
                type={reveal ? 'text' : 'password'}
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="pr-12"
                aria-invalid={invalidCredentials || undefined}
                aria-describedby={errorDescribedBy}
                data-testid="login-password"
              />
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="absolute right-0 top-0 rounded-l-none rounded-r-lg text-muted-foreground focus-visible:ring-offset-surface"
                aria-label={reveal ? en.auth.hidePassword : en.auth.showPassword}
                aria-pressed={reveal}
                data-testid="login-reveal"
                onClick={() => setReveal((r) => !r)}
              >
                {reveal ? (
                  <EyeOff className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Eye className="h-4 w-4" aria-hidden="true" />
                )}
              </Button>
            </div>
          </div>
          <Button
            type="submit"
            className="w-full"
            disabled={!hydrated || submitting}
            aria-busy={submitting}
            data-testid="login-submit"
          >
            {submitting ? en.auth.signInWorking : en.auth.signIn}
          </Button>
        </form>
        <p className="mt-6 border-t border-border pt-4 text-xs leading-5 text-muted-foreground">
          {en.auth.authorizationNotice}
        </p>
      </CardContent>
    </Card>
  );
}
