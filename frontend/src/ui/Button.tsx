import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router-dom'

type Variant = 'primary' | 'secondary' | 'ghost' | 'text'

type Props = {
  variant?: Variant
  to?: string
  href?: string
  children: ReactNode
} & ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ variant = 'primary', to, href, className, children, type = 'button', ...rest }: Props) {
  const cls = ['btn', variant, className].filter(Boolean).join(' ')
  if (to) {
    return (
      <Link className={cls} to={to}>
        {children}
      </Link>
    )
  }
  if (href) {
    return (
      <a className={cls} href={href}>
        {children}
      </a>
    )
  }
  return (
    <button className={cls} type={type} {...rest}>
      {children}
    </button>
  )
}
