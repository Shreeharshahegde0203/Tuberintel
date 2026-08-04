/* eslint-disable react-refresh/only-export-components */
import { createClient, type Session, type User } from '@supabase/supabase-js'
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type AuthUser = {
  id: string
  email: string
  name: string
  avatarUrl: string
}

type AuthContextValue = {
  user: AuthUser | null
  session: Session | null
  loading: boolean
  configured: boolean
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

const supabaseUrl = String(import.meta.env.VITE_SUPABASE_URL || '').trim()
const supabaseKey = String(
  import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY || import.meta.env.VITE_SUPABASE_ANON_KEY || '',
).trim()

const configured = Boolean(
  supabaseUrl &&
    supabaseKey &&
    !supabaseUrl.includes('YOUR_PROJECT_ID') &&
    !supabaseKey.includes('YOUR_PUBLISHABLE_KEY'),
)

const supabase = configured ? createClient(supabaseUrl, supabaseKey) : null

function toAuthUser(user: User | null): AuthUser | null {
  if (!user) return null

  const metadata = user.user_metadata || {}
  return {
    id: user.id,
    email: user.email || '',
    name: String(metadata.full_name || metadata.name || user.email?.split('@')[0] || 'TuberIntel user'),
    avatarUrl: String(metadata.avatar_url || metadata.picture || ''),
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<Session | null>(null)
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!supabase) {
      setLoading(false)
      return
    }

    let mounted = true

    supabase.auth.getSession().then(({ data }) => {
      if (!mounted) return
      setSession(data.session)
      setUser(toAuthUser(data.session?.user ?? null))
      setLoading(false)
    })

    const { data: listener } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession)
      setUser(toAuthUser(nextSession?.user ?? null))
      setLoading(false)
    })

    return () => {
      mounted = false
      listener.subscription.unsubscribe()
    }
  }, [])

  const signInWithGoogle = async () => {
    if (!supabase) {
      throw new Error('Google Sign-In is not configured. Add your Supabase project URL and publishable key to frontend/.env.local.')
    }

    setLoading(true)
    try {
      const { error } = await supabase.auth.signInWithOAuth({
        provider: 'google',
        options: {
          redirectTo: `${window.location.origin}/`,
        },
      })
      if (error) throw error
    } finally {
      setLoading(false)
    }
  }

  const signOut = async () => {
    if (supabase) {
      const { error } = await supabase.auth.signOut()
      if (error) throw error
    }
    setSession(null)
    setUser(null)
  }

  const value = useMemo(
    () => ({ user, session, loading, configured, signInWithGoogle, signOut }),
    [user, session, loading],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const value = useContext(AuthContext)
  if (!value) throw new Error('useAuth must be used inside AuthProvider')
  return value
}

export function getAccessToken() {
  return supabase?.auth.getSession().then(({ data }) => data.session?.access_token ?? null) ?? Promise.resolve(null)
}
