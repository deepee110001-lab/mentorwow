import { Navigate, useSearchParams } from 'react-router-dom'

export function Register() {
  const [params] = useSearchParams()
  const qs = params.toString()
  return <Navigate to={qs ? `/login?${qs}` : '/login'} replace />
}
