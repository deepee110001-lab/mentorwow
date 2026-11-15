import { avatarStyle, initials } from '../lib'

export function Avatar({ handle, accent, size = 44 }: { handle: string; accent: string; size?: number }) {
  return (
    <span className="avatar" style={{ ...avatarStyle(accent), width: size, height: size, fontSize: size > 50 ? 18 : 13 }}>
      {initials(handle)}
    </span>
  )
}
