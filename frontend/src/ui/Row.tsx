import type { ReactNode } from 'react'

export function Row({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={['row-actions', className].filter(Boolean).join(' ')}>{children}</div>
}
