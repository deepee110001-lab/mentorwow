import type { ReactNode } from 'react'

export function Banner({ tone = 'error', children }: { tone?: 'error' | 'success'; children: ReactNode }) {
  return <div className={tone === 'success' ? 'success' : 'error'}>{children}</div>
}
