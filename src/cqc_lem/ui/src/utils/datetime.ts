export function formatInTimezone(
  isoString: string | null | undefined,
  tz: string,
  options?: Intl.DateTimeFormatOptions,
): string {
  if (!isoString) return '—'
  try {
    return new Intl.DateTimeFormat('en-US', {
      timeZone: tz,
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      ...options,
    }).format(new Date(isoString))
  } catch {
    return new Date(isoString).toLocaleString()
  }
}
