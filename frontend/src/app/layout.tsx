import type { Metadata } from 'next';

import '../styles/globals.css';
import { en } from '@/content/en';
import { getStoredTheme } from '@/lib/theme-server';

export const metadata: Metadata = {
  title: {
    default: en.app.name,
    template: `%s | ${en.app.name}`,
  },
  description: 'Phishing Simulation + Detection Platform',
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const theme = await getStoredTheme();

  return (
    <html
      lang="en"
      className={theme ?? undefined}
      data-theme={theme ?? undefined}
      suppressHydrationWarning
    >
      <body className="min-h-dvh bg-background text-foreground antialiased">
        <a href="#main-content" className="skip-link">
          {en.app.skipToContent}
        </a>
        {children}
      </body>
    </html>
  );
}
