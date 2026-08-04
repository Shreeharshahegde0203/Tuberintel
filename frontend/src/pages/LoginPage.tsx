import { BadgeCheck, Languages, Leaf, ShieldCheck, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useI18n } from '../i18n/I18nContext'
import '../auth-login-compact.css'

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" className="auth-google-mark">
      <path fill="#4285F4" d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.39a4.61 4.61 0 0 1-2 3.02v2.54h3.24c1.9-1.75 2.97-4.33 2.97-7.41Z" />
      <path fill="#34A853" d="M12 22c2.7 0 4.98-.9 6.64-2.36l-3.24-2.54c-.9.6-2.05.96-3.4.96-2.61 0-4.82-1.76-5.61-4.13H3.04v2.62A10 10 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.39 13.93A6.02 6.02 0 0 1 6.08 12c0-.67.12-1.32.31-1.93V7.45H3.04A10 10 0 0 0 2 12c0 1.61.39 3.13 1.04 4.55l3.35-2.62Z" />
      <path fill="#EA4335" d="M12 5.94c1.47 0 2.79.51 3.83 1.5l2.88-2.88A9.65 9.65 0 0 0 12 2a10 10 0 0 0-8.96 5.45l3.35 2.62C7.18 7.7 9.39 5.94 12 5.94Z" />
    </svg>
  )
}

export default function LoginPage() {
  const { user, configured, loading, signInWithGoogle } = useAuth()
  const { language, setLanguage, t } = useI18n()
  const location = useLocation()
  const [error, setError] = useState('')

  const copy = language === 'kn'
    ? {
        secure: 'ಸುರಕ್ಷಿತ Google ಸೈನ್-ಇನ್',
        kicker: 'ರೈತ ಕೇಂದ್ರಿತ ಆಲೂಗಡ್ಡೆ ಮಾಹಿತಿ',
        title: 'ಉತ್ತಮ ಆಲೂಗಡ್ಡೆ ನಿರ್ಧಾರಗಳಿಗೆ ಸರಳ ಆರಂಭ.',
        subtitle: 'ಮಾರುಕಟ್ಟೆ ಬೆಲೆ, ಗುಣಮಟ್ಟ ವಿಶ್ಲೇಷಣೆ ಮತ್ತು ನಿಮ್ಮ ಕೃಷಿ ಇತಿಹಾಸವನ್ನು ಒಂದೇ ಸುರಕ್ಷಿತ ಖಾತೆಯಿಂದ ಬಳಸಿ.',
        cardTitle: 'TuberIntel ಗೆ ಸ್ವಾಗತ',
        cardText: 'ನಿಮ್ಮ Google ಖಾತೆಯೊಂದಿಗೆ ಸುರಕ್ಷಿತವಾಗಿ ಮುಂದುವರಿಯಿರಿ.',
        button: 'Google ಮೂಲಕ ಮುಂದುವರಿಯಿರಿ',
        signingIn: 'Google ಗೆ ತೆರೆಯಲಾಗುತ್ತಿದೆ…',
        benefit1: 'ಮಂಡಿ ಬೆಲೆ ಮಾಹಿತಿ',
        benefit2: 'ಬ್ಯಾಚ್ ವಿಶ್ಲೇಷಣೆ ಇತಿಹಾಸ',
        benefit3: 'ಇಂಗ್ಲಿಷ್ ಮತ್ತು ಕನ್ನಡ',
        privacy: 'ನಿಮ್ಮ ಖಾತೆಯನ್ನು ಸುರಕ್ಷಿತವಾಗಿ ಗುರುತಿಸಲು ಮಾತ್ರ Google ಸೈನ್-ಇನ್ ಬಳಸಲಾಗುತ್ತದೆ.',
        notConfigured: 'Google Sign-In ಇನ್ನೂ ಸಂಪರ್ಕಗೊಂಡಿಲ್ಲ. frontend/.env.local ನಲ್ಲಿ Supabase URL ಮತ್ತು publishable key ಸೇರಿಸಿ.',
      }
    : {
        secure: 'Secure Google sign-in',
        kicker: 'Farmer-first potato intelligence',
        title: 'Better potato decisions begin with one simple sign-in.',
        subtitle: 'Access mandi prices, quality analysis and your farm history from one secure account.',
        cardTitle: 'Welcome to TuberIntel',
        cardText: 'Continue securely with your Google account.',
        button: 'Continue with Google',
        signingIn: 'Opening Google…',
        benefit1: 'Mandi price intelligence',
        benefit2: 'Batch analysis history',
        benefit3: 'English and Kannada',
        privacy: 'Google Sign-In is used only to identify and secure your TuberIntel account.',
        notConfigured: 'Google Sign-In is not connected yet. Add the Supabase URL and publishable key in frontend/.env.local.',
      }

  if (user) {
    const from = (location.state as { from?: string } | null)?.from || '/'
    return <Navigate to={from} replace />
  }

  const handleGoogleSignIn = async () => {
    setError('')
    try {
      await signInWithGoogle()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Google authentication failed. Please try again.')
    }
  }

  return (
    <main className="auth-google-page">
      <div className="auth-google-orb auth-google-orb-one" />
      <div className="auth-google-orb auth-google-orb-two" />

      <header className="auth-google-header">
        <div className="auth-google-brand">
          <span className="auth-google-brand-mark"><Leaf size={20} strokeWidth={2.2} /></span>
          <div>
            <strong>{t('brand.name')}</strong>
            <small>{t('brand.tagline')}</small>
          </div>
        </div>

        <div className="auth-google-actions">
          <span className="auth-google-secure"><ShieldCheck size={15} /> {copy.secure}</span>
          <button
            type="button"
            className="auth-google-language"
            onClick={() => setLanguage(language === 'en' ? 'kn' : 'en')}
          >
            <Languages size={16} />
            <span>{language === 'en' ? 'ಕನ್ನಡ' : 'English'}</span>
          </button>
        </div>
      </header>

      <section className="auth-google-content">
        <div className="auth-google-intro">
          <span className="auth-google-kicker"><Sparkles size={14} /> {copy.kicker}</span>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>

        <div className="auth-google-stage">
          <div className="auth-google-mascot-wrap" aria-label={t('auth.mascotAlt')}>
            <span className="auth-google-mascot-shadow" />
            <img src="/brand/tuber-mitra.png" alt={t('auth.mascotAlt')} className="auth-google-mascot" />
          </div>

          <div className="auth-google-card">
            <div className="auth-google-card-heading">
              <span className="auth-google-card-icon"><ShieldCheck size={20} /></span>
              <div>
                <h2>{copy.cardTitle}</h2>
                <p>{copy.cardText}</p>
              </div>
            </div>

            {!configured && <div className="auth-google-alert" role="alert">{copy.notConfigured}</div>}
            {error && <div className="auth-google-alert error" role="alert">{error}</div>}

            <button
              type="button"
              className="auth-google-button"
              onClick={() => void handleGoogleSignIn()}
              disabled={!configured || loading}
            >
              <GoogleMark />
              <span>{loading ? copy.signingIn : copy.button}</span>
            </button>

            <div className="auth-google-benefits">
              <span><BadgeCheck size={14} /> {copy.benefit1}</span>
              <span><BadgeCheck size={14} /> {copy.benefit2}</span>
              <span><BadgeCheck size={14} /> {copy.benefit3}</span>
            </div>

            <div className="auth-google-privacy">
              <ShieldCheck size={14} />
              <span>{copy.privacy}</span>
            </div>
          </div>
        </div>
      </section>

      <footer className="auth-google-footer">
        <span>{t('auth.footerLine')}</span>
        <span><i /> {t('auth.systemReady')}</span>
      </footer>
    </main>
  )
}
