export function initials(handle: string) {
  return handle
    .split('-')
    .slice(0, 2)
    .map((part) => part[0] ?? '')
    .join('')
    .toUpperCase()
}

export function avatarStyle(accent: string) {
  return { background: `${accent}22`, color: accent }
}

export function formatWhen(value: string) {
  return new Date(value).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

export function clock(seconds: number) {
  const safe = Math.max(0, Math.floor(seconds))
  const m = Math.floor(safe / 60)
  const s = safe % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}
