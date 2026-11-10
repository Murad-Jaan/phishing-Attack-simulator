export type Theme = 'light' | 'dark';

export const THEME_COOKIE = 'phishsim_theme';
export const THEME_MAX_AGE_SECONDS = 60 * 60 * 24 * 365;

export function parseTheme(value: string | null | undefined): Theme | null {
  return value === 'light' || value === 'dark' ? value : null;
}
