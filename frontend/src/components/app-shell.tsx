'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  BarChart3,
  FileText,
  LayoutDashboard,
  MailSearch,
  Menu,
  Send,
  Settings as SettingsIcon,
  ShieldCheck,
  Users,
  X,
  type LucideIcon,
} from 'lucide-react';

import SignOutButton from '@/components/auth/sign-out-button';
import ThemeToggle from '@/components/theme-toggle';
import { Badge } from '@/components/ui/badge';
import { en } from '@/content/en';
import type { SessionUser } from '@/lib/auth/session';
import type { Theme } from '@/lib/theme';
import { cn } from '@/lib/utils';

interface AppShellProps {
  user: SessionUser;
  initialTheme: Theme | null;
  children: ReactNode;
}

interface NavItem {
  href: string;
  label: string;
  icon: LucideIcon;
}

const primaryNav: NavItem[] = [
  { href: '/', label: en.nav.dashboard, icon: LayoutDashboard },
  { href: '/campaigns', label: en.nav.campaigns, icon: Send },
  { href: '/templates', label: en.nav.templates, icon: FileText },
  { href: '/groups', label: en.nav.groups, icon: Users },
  { href: '/reports', label: en.nav.reports, icon: BarChart3 },
  { href: '/analyzer', label: en.nav.analyzer, icon: MailSearch },
];

const settingsNav: NavItem = { href: '/settings', label: en.nav.settings, icon: SettingsIcon };

function isActivePath(pathname: string, href: string) {
  return href === '/' ? pathname === '/' : pathname.startsWith(href);
}

export function AppShell({ user, initialTheme, children }: AppShellProps) {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const isAdmin = user.role === 'admin';
  const navItems = isAdmin ? [...primaryNav, settingsNav] : primaryNav;
  const initials =
    user.display_name
      .split(/\s+/)
      .map((part) => part[0])
      .filter(Boolean)
      .slice(0, 2)
      .join('')
      .toUpperCase() || user.email.slice(0, 2).toUpperCase();

  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!mobileOpen) {
      return;
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMobileOpen(false);
        menuButtonRef.current?.focus();
      }
    }
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [mobileOpen]);

  return (
    <div className="flex min-h-dvh bg-background">
      <aside
        id="app-sidebar"
        aria-label={en.nav.sidebarLabel}
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-60 flex-col border-r border-border bg-surface transition-transform duration-200 motion-reduce:transition-none lg:sticky lg:top-0 lg:z-auto lg:h-dvh lg:translate-x-0',
          mobileOpen ? 'visible translate-x-0' : 'invisible -translate-x-full lg:visible',
        )}
      >
        <Link
          href="/"
          className="flex min-h-16 items-center gap-2 border-b border-border px-4"
          onClick={() => setMobileOpen(false)}
        >
          <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary-tint text-primary-strong">
            <ShieldCheck className="h-5 w-5" aria-hidden="true" />
          </span>
          <span className="text-sm font-semibold leading-5 text-foreground">{en.app.name}</span>
        </Link>

        <nav className="flex-1 overflow-y-auto p-3" aria-label={en.nav.mainLabel}>
          <ul className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = isActivePath(pathname, item.href);
              return (
                <li key={item.href}>
                  <Link
                    href={item.href}
                    aria-current={active ? 'page' : undefined}
                    onClick={() => setMobileOpen(false)}
                    className={cn(
                      'flex min-h-11 items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background motion-reduce:transition-none',
                      active
                        ? 'bg-primary-tint text-primary-strong'
                        : 'text-strong hover:bg-surface-muted hover:text-foreground',
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="border-t border-border p-4">
          <div className="mb-3 flex items-center gap-3">
            <span
              className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-primary-tint text-xs font-bold text-primary-strong"
              aria-hidden="true"
            >
              {initials}
            </span>
            <div className="min-w-0">
              <p className="text-xs text-muted-foreground">{en.auth.signedInAs}</p>
              <p className="truncate text-sm font-semibold text-foreground">{user.display_name}</p>
              <p className="truncate text-xs text-muted-foreground">{user.email}</p>
            </div>
          </div>
          <div className="mb-3 flex items-center justify-between gap-2">
            <Badge variant="secondary">
              <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="sr-only">Role: </span>
              {user.role}
            </Badge>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-medium text-muted-foreground">{en.theme.label}</span>
              <ThemeToggle initialTheme={initialTheme} />
            </div>
          </div>
          <SignOutButton />
        </div>
      </aside>

      {mobileOpen ? (
        <button
          type="button"
          className="fixed inset-0 z-30 bg-foreground/30 lg:hidden"
          aria-label={en.nav.dismissMenu}
          onClick={() => setMobileOpen(false)}
        />
      ) : null}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-3 border-b border-border bg-surface px-4 lg:hidden">
          <Link
            href="/"
            className="flex min-w-0 items-center gap-2"
            onClick={() => setMobileOpen(false)}
          >
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary-tint text-primary-strong">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
            </span>
            <span className="truncate text-sm font-semibold text-foreground">{en.app.name}</span>
          </Link>
          <button
            ref={menuButtonRef}
            type="button"
            className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-foreground hover:bg-surface-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
            aria-controls="app-sidebar"
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? en.nav.closeMenu : en.nav.openMenu}
            onClick={() => setMobileOpen((open) => !open)}
          >
            {mobileOpen ? (
              <X className="h-5 w-5" aria-hidden="true" />
            ) : (
              <Menu className="h-5 w-5" aria-hidden="true" />
            )}
          </button>
        </header>

        <main
          id="main-content"
          tabIndex={-1}
          className="flex-1 px-4 py-6 sm:px-6 lg:px-8 lg:py-8"
        >
          <div className="mx-auto w-full max-w-[1136px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
