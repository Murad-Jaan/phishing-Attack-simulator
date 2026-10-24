import type { Metadata } from 'next'
import '../styles/globals.css'
import { en } from '@/content/en'

export const metadata: Metadata = {
  title: en.app.name,
  description: 'Phishing Simulation + Detection Platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 focus:z-50 focus:bg-white focus:text-black focus:px-4 focus:py-2">
          {en.app.skipToContent}
        </a>
        <header role="banner">
          <nav role="navigation" aria-label="Main navigation">
            {/* Navigation will be added in later phases */}
          </nav>
        </header>
        <main id="main-content" role="main" tabIndex={-1}>
          {children}
        </main>
      </body>
    </html>
  )
}
