'use client';

import { useEffect, useState } from 'react';
import { Moon, Sun } from 'lucide-react';

import { en } from '@/content/en';
import { THEME_COOKIE, THEME_MAX_AGE_SECONDS, type Theme } from '@/lib/theme';
import { cn } from '@/lib/utils';

interface ThemeToggleProps {
  initialTheme: Theme | null;
  className?: string;
}

export default function ThemeToggle({ initialTheme, className }: ThemeToggleProps) {
  const [theme, setTheme] = useState<Theme | null>(initialTheme);

  useEffect(() => {
    if (initialTheme !== null) {
      setTheme(initialTheme);
      return;
    }

    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => setTheme(media.matches ? 'dark' : 'light');
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [initialTheme]);

  const isDark = theme === 'dark';
  const label =
    theme === null
      ? en.theme.toggle
      : isDark
        ? en.theme.switchToLight
        : en.theme.switchToDark;

  function toggleTheme() {
    const current =
      theme ?? (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    const next: Theme = current === 'dark' ? 'light' : 'dark';
    const root = document.documentElement;

    root.classList.remove('light', 'dark');
    root.classList.add(next);
    root.dataset.theme = next;

    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${THEME_COOKIE}=${next}; Path=/; Max-Age=${THEME_MAX_AGE_SECONDS}; SameSite=Lax${secure}`;
    setTheme(next);
  }

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={label}
      title={label}
      data-testid="theme-toggle"
      className={cn(
        'inline-flex h-11 w-11 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background motion-reduce:transition-none',
        className,
      )}
    >
      {isDark ? (
        <Sun className="h-5 w-5" aria-hidden="true" />
      ) : (
        <Moon className="h-5 w-5" aria-hidden="true" />
      )}
    </button>
  );
}
