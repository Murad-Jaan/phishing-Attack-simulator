import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

export function middleware(request: NextRequest) {
  const nonce = Buffer.from(crypto.randomUUID()).toString('base64')
  
  const requestHeaders = new Headers(request.headers)
  requestHeaders.set('x-nonce', nonce)
  
  const response = NextResponse.next({
    request: {
      headers: requestHeaders,
    },
  })
  
  const isProd = process.env.NODE_ENV === 'production' || process.env.APP_ENV === 'production'
  
  if (isProd) {
    response.headers.set(
      'Content-Security-Policy',
      `default-src 'self'; script-src 'self' 'nonce-${nonce}' 'strict-dynamic'; style-src 'self' 'nonce-${nonce}'; object-src 'none'; base-uri 'self';`
    )
  } else {
    response.headers.set(
      'Content-Security-Policy',
      `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';`
    )
  }
  
  return response
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico).*)'],
}
