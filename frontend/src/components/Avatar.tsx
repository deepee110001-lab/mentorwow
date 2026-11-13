import { avatarStyle, initials } from '../lib'

export function Avatar({ name, accent, size = 44 }: { name: string; accent: string; size?: number }) {
  return (
    <span className="avatar" style={{ ...avatarStyle(accent), width: size, height: size, fontSize: size > 50 ? 18 : 13 }}>
      {initials(name)}
    </span>
  )
}
