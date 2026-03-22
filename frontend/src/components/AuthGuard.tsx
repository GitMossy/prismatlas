import { useEffect, useState } from 'react'
import { supabase } from '@/lib/supabase'

const PRISM_LOGIN_URL = (import.meta as unknown as { env: Record<string, string> }).env.VITE_PRISM_LOGIN_URL ?? 'https://prismplatform.ai/login'

interface AuthGuardProps {
  children: React.ReactNode
}

export function AuthGuard({ children }: AuthGuardProps) {
  const [checked, setChecked] = useState(false)
  const [authenticated, setAuthenticated] = useState(false)

  useEffect(() => {
    supabase.auth.getUser().then(({ data: { user } }) => {
      if (user) {
        setAuthenticated(true)
      } else {
        const redirectTo = encodeURIComponent(window.location.href)
        window.location.href = `${PRISM_LOGIN_URL}?redirectTo=${redirectTo}`
      }
      setChecked(true)
    })

    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!session) {
        const redirectTo = encodeURIComponent(window.location.href)
        window.location.href = `${PRISM_LOGIN_URL}?redirectTo=${redirectTo}`
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  if (!checked || !authenticated) {
    return (
      <div className="flex h-screen w-screen items-center justify-center bg-background">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    )
  }

  return <>{children}</>
}
