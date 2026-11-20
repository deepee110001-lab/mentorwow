import { SocialAuth } from './SocialAuth'

/** @deprecated Use SocialAuth. Kept so existing imports keep working. */
export function GoogleButton({ onCredential }: { onCredential: (credential: string) => void; label?: string }) {
  return <SocialAuth onGoogle={onCredential} />
}
