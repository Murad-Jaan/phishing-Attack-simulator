import type { Metadata } from 'next'
import '../styles/globals.css'
import { en } from '@/content/en'
import { headers } from 'next/headers'
import Link from 'next/link'
import { getSessionUser } from '@/lib/auth/session'

export const metadata: Metadata = {
  title: en.app.name,
  description: 'Phishing Simulation + Detection Platform',
}

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const nonce = (await headers()).get('x-nonce') || ''
  const user = await getSessionUser()
  const canManageGroups = user?.role === 'admin' || user?.role === 'analyst'

  return (
    <html lang="en">
      <head nonce={nonce} />
      <body>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-white focus:text-black focus:px-4 focus:py-2">
          {en.app.skipToContent}
        </a>
        <header role="banner" className="border-b border-border bg-background">
          <nav
            role="navigation"
            aria-label="Main navigation"
            className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-4 px-4 py-3"
          >
            <Link href="/" className="font-semibold text-foreground">
              {en.app.name}
            </Link>
            {user && (
              <Link href="/" className="text-sm text-muted-foreground hover:text-foreground">
                {en.nav.dashboard}
              </Link>
            )}
            {user && canManageGroups && (
              <Link href="/groups" className="text-sm text-muted-foreground hover:text-foreground">
                {en.nav.groups}
              </Link>
            )}
          </nav>
        </header>
        <main id="main-content" role="main" tabIndex={-1}>
          {children}
        </main>
      </body>
    </html>
  )
}
