import type { ElementType, ReactNode } from 'react'

type Variant = 'eyebrow' | 'display' | 'title' | 'heading' | 'lede' | 'body' | 'muted' | 'quote'

const MAP: Record<Variant, { as: ElementType; className: string }> = {
  eyebrow: { as: 'p', className: 'eyebrow' },
  display: { as: 'h1', className: 'display' },
  title: { as: 'h1', className: 'title' },
  heading: { as: 'h2', className: 'heading' },
  lede: { as: 'p', className: 'lede' },
  body: { as: 'p', className: 'body' },
  muted: { as: 'p', className: 'muted' },
  quote: { as: 'p', className: 'quote' },
}

export function Text({
  variant = 'body',
  as,
  children,
  className,
}: {
  variant?: Variant
  as?: ElementType
  children: ReactNode
  className?: string
}) {
  const spec = MAP[variant]
  const Tag = as ?? spec.as
  return <Tag className={[spec.className, className].filter(Boolean).join(' ')}>{children}</Tag>
}
