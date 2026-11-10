/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import type { Session, User } from '@supabase/supabase-js'
import { supabase } from './supabase'

export type AuthUser = {
  id: string
  phone: string
  name?: string
  email?: string
  avatarUrl?: string
}

type AuthContextValue = {
  user: AuthUser | null
  loading: boolean
  mode: 'demo' | 'supabase'
  sendOtp: (phone: string) => Promise<void>
  verifyOtp: (phone: string, token: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signOut: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)
const storageKey = 'tuberintel-session'

function normalizedPhone(phone: string) {
  const digits = phone.replace(/\D/g, '')

  if (digits.length === 10) return `+91${digits}`
  if (digits.startsWith('91') && digits.length === 12) return `+${digits}`

  return phone.startsWith('+') ? phone : `+${digits}`
}

function readUser(): AuthUser | null {
  try {
    const raw = localStorage.getItem(storageKey)

    if (!raw) return null

    const parsed = JSON.parse(raw) as {
      user?: AuthUser
      expires_at?: number
    }

    if (parsed.expires_at && parsed.expires_at * 1000 < Date.now()) {
      localStorage.removeItem(storageKey)
      return null
    }

    return parsed.user ?? null
  } catch {
    localStorage.removeItem(storageKey)
    return null
  }
}

function mapSupabaseUser(user: User): AuthUser {
  const metadata = user.user_metadata || {}

  return {
    id: user.id,
    phone: user.phone || '',
    email: user.email || undefined,
    name:
      metadata.full_name ||
      metadata.name ||
      user.email?.split('@')[0] ||
      'Farmer',
    avatarUrl:
      metadata.avatar_url ||
      metadata.picture ||
      undefined,
  }
}

function persistSupabaseSession(session: Session | null): AuthUser | null {
  if (!session) {
    localStorage.removeItem(storageKey)
    return null
  }

  const appUser = mapSupabaseUser(session.user)

  localStorage.setItem(
    storageKey,
    JSON.stringify({
      user: appUser,
      access_token: session.access_token,
      refresh_token: session.refresh_token,
      expires_at: session.expires_at,
    }),
  )

  return appUser
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const mode = (
    import.meta.env.VITE_AUTH_MODE === 'supabase'
      ? 'supabase'
      : 'demo'
  ) as 'demo' | 'supabase'

  const [user, setUser] = useState<AuthUser | null>(() =>
    mode === 'demo' ? readUser() : null,
  )

  const [loading, setLoading] = useState(mode === 'supabase')

  useEffect(() => {
    if (mode !== 'supabase') return

    let mounted = true

    const restoreSession = async () => {
      try {
        const {
          data: { session },
          error,
        } = await supabase.auth.getSession()

        if (error) throw error

        if (mounted) {
          setUser(persistSupabaseSession(session))
        }
      } catch {
        if (mounted) {
          localStorage.removeItem(storageKey)
          setUser(null)
        }
      } finally {
        if (mounted) setLoading(false)
      }
    }

    void restoreSession()

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (!mounted) return

      setUser(persistSupabaseSession(session))
      setLoading(false)
    })

    return () => {
      mounted = false
      subscription.unsubscribe()
    }
  }, [mode])

  const sendOtp = async (phone: string) => {
    const value = normalizedPhone(phone)

    if (!/^\+\d{10,15}$/.test(value)) {
      throw new Error('Enter a valid mobile number')
    }

    if (mode === 'demo') {
      sessionStorage.setItem('tuberintel-demo-phone', value)
      return
    }

    setLoading(true)

    try {
      const { error } = await supabase.auth.signInWithOtp({
        phone: value,
      })

      if (error) throw error
    } finally {
      setLoading(false)
    }
  }

  const verifyOtp = async (phone: string, token: string) => {
    const value = normalizedPhone(phone)

    if (mode === 'demo') {
      if (token !== '123456') {
        throw new Error('For local demo use OTP 123456')
      }

      const demoUser: AuthUser = {
        id: `demo-${value}`,
        phone: value,
        name: 'Farmer',
      }

      localStorage.setItem(
        storageKey,
        JSON.stringify({
          user: demoUser,
          expires_at: Math.floor(Date.now() / 1000) + 86400 * 30,
        }),
      )

      setUser(demoUser)
      return
    }

    setLoading(true)

    try {
      const { data, error } = await supabase.auth.verifyOtp({
        phone: value,
        token,
        type: 'sms',
      })

      if (error) throw error
      if (!data.session) throw new Error('OTP verification failed')

      setUser(persistSupabaseSession(data.session))
    } finally {
      setLoading(false)
    }
  }

  const signInWithGoogle = async () => {
    if (mode !== 'supabase') {
      throw new Error('Google authentication requires Supabase auth mode')
    }

    setLoading(true)

    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/login`,
      },
    })

    if (error) {
      setLoading(false)
      throw error
    }
  }

  const signOut = async () => {
    try {
      if (mode === 'supabase') {
        await supabase.auth.signOut()
      }
    } finally {
      localStorage.removeItem(storageKey)
      sessionStorage.removeItem('tuberintel-demo-phone')
      setUser(null)
    }
  }

  const value = useMemo(
    () => ({
      user,
      loading,
      mode,
      sendOtp,
      verifyOtp,
      signInWithGoogle,
      signOut,
    }),
    [user, loading, mode],
  )

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const value = useContext(AuthContext)

  if (!value) {
    throw new Error('useAuth must be used inside AuthProvider')
  }

  return value
}