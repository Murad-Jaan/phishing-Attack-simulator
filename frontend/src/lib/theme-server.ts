import { cookies } from 'next/headers';

import { parseTheme, THEME_COOKIE, type Theme } from './theme';

export async function getStoredTheme(): Promise<Theme | null> {
  const cookieStore = await cookies();
  return parseTheme(cookieStore.get(THEME_COOKIE)?.value);
}
