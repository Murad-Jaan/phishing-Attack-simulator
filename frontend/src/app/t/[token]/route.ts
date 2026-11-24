import { NextResponse, type NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ token: string }> },
) {
  const { token } = await context.params;
  const api = process.env.API_INTERNAL_URL || 'http://127.0.0.1:8000';
  const forwardedProto = request.headers.get('x-forwarded-proto');
  const forwardedHost = request.headers.get('x-forwarded-host');
  const host = forwardedHost || request.headers.get('host') || request.nextUrl.host;
  const proto = forwardedProto || request.nextUrl.protocol.replace(':', '');
  const origin = `${proto}://${host}`;
  const fallback = new URL(
    `/learn/${encodeURIComponent(token)}`,
    origin,
  );

  try {
    const response = await fetch(
      `${api}/t/${encodeURIComponent(token)}`,
      {
        headers: {
          'user-agent': request.headers.get('user-agent') ?? '',
        },
        redirect: 'manual',
        cache: 'no-store',
      },
    );
    const location = response.headers.get('location');
    if (location) {
      const target = new URL(location);
      const redirect = NextResponse.redirect(
        new URL(`${target.pathname}${target.search}`, origin),
        302,
      );
      redirect.headers.set('Cache-Control', 'no-store');
      redirect.headers.set('Referrer-Policy', 'no-referrer');
      return redirect;
    }
  } catch {
    // The awareness page remains reachable even if the API is unavailable.
  }

  const redirect = NextResponse.redirect(fallback, 302);
  redirect.headers.set('Cache-Control', 'no-store');
  redirect.headers.set('Referrer-Policy', 'no-referrer');
  return redirect;
}
