import type { Metadata } from 'next'
import '../styles/globals.css'
import { en } from '@/content/en'
import { headers } from 'next/headers'

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
  
  return (
    <html lang="en">
      <head nonce={nonce} />
      <body>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-white focus:text-black focus:px-4 focus:py-2">
          {en.app.skipToContent}
        </a>
        <header role="banner">
          <nav role="navigation" aria-label="Main navigation">
          </nav>
        </header>
        <main id="main-content" role="main" tabIndex={-1}>
          {children}
        </main>
      </body>
    </html>
  )
}
