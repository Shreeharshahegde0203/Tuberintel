import {
  ArrowLeft,
  ArrowRight,
  BadgeCheck,
  Languages,
  Leaf,
  LockKeyhole,
  MessageSquareText,
  Phone,
  ShieldCheck,
} from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { useI18n } from '../i18n/I18nContext'

const OTP_LENGTH = 6

export default function LoginPage() {
  const {
    user,
    mode,
    loading,
    sendOtp,
    verifyOtp,
    signInWithGoogle,
  } = useAuth()

  const { language, setLanguage, t } = useI18n()
  const location = useLocation()

  const [phone, setPhone] = useState('')
  const [otpDigits, setOtpDigits] = useState<string[]>(
    Array(OTP_LENGTH).fill(''),
  )
  const [step, setStep] = useState<'phone' | 'otp'>('phone')
  const [error, setError] = useState('')
  const [seconds, setSeconds] = useState(0)

  const otpRefs = useRef<Array<HTMLInputElement | null>>([])

  useEffect(() => {
    if (!seconds) return

    const timer = window.setInterval(
      () => setSeconds((value) => Math.max(0, value - 1)),
      1000,
    )

    return () => window.clearInterval(timer)
  }, [seconds])

  useEffect(() => {
    if (step === 'otp') {
      window.setTimeout(() => otpRefs.current[0]?.focus(), 120)
    }
  }, [step])

  if (user) {
    const from =
      (location.state as { from?: string } | null)?.from || '/'

    return <Navigate to={from} replace />
  }

  const requestOtp = async (event?: React.FormEvent) => {
    event?.preventDefault()
    setError('')

    try {
      await sendOtp(phone)

      setOtpDigits(Array(OTP_LENGTH).fill(''))
      setStep('otp')
      setSeconds(30)
    } catch (err: any) {
      setError(err.message || t('auth.failed'))
    }
  }

  const confirmOtp = async (event: React.FormEvent) => {
    event.preventDefault()
    setError('')

    try {
      await verifyOtp(phone, otpDigits.join(''))
    } catch (err: any) {
      setError(err.message || t('auth.failed'))
    }
  }

  const handleGoogleSignIn = async () => {
    setError('')

    try {
      await signInWithGoogle()
    } catch (err: any) {
      setError(err.message || 'Google sign-in failed')
    }
  }

  const updateOtpDigit = (index: number, value: string) => {
    const digit = value.replace(/\D/g, '').slice(-1)

    setOtpDigits((current) => {
      const next = [...current]
      next[index] = digit
      return next
    })

    if (digit && index < OTP_LENGTH - 1) {
      otpRefs.current[index + 1]?.focus()
    }
  }

  const handleOtpKeyDown = (
    index: number,
    event: React.KeyboardEvent<HTMLInputElement>,
  ) => {
    if (
      event.key === 'Backspace' &&
      !otpDigits[index] &&
      index > 0
    ) {
      otpRefs.current[index - 1]?.focus()
    }

    if (event.key === 'ArrowLeft' && index > 0) {
      otpRefs.current[index - 1]?.focus()
    }

    if (
      event.key === 'ArrowRight' &&
      index < OTP_LENGTH - 1
    ) {
      otpRefs.current[index + 1]?.focus()
    }
  }

  const handleOtpPaste = (
    event: React.ClipboardEvent<HTMLDivElement>,
  ) => {
    const pasted = event.clipboardData
      .getData('text')
      .replace(/\D/g, '')
      .slice(0, OTP_LENGTH)

    if (!pasted) return

    event.preventDefault()

    const digits = Array(OTP_LENGTH).fill('')

    pasted.split('').forEach((digit, index) => {
      digits[index] = digit
    })

    setOtpDigits(digits)

    otpRefs.current[
      Math.min(pasted.length, OTP_LENGTH) - 1
    ]?.focus()
  }

  const otpComplete = otpDigits.every(Boolean)

  const maskedPhone =
    phone.length === 10
      ? `+91 ${phone.slice(0, 2)}••• ••${phone.slice(-3)}`
      : `+91 ${phone}`

  return (
    <main className="auth-page">
      <section className="auth-visual-panel">
        <div className="auth-visual-orb auth-visual-orb-one" />
        <div className="auth-visual-orb auth-visual-orb-two" />

        <header className="auth-brand-row">
          <div className="auth-brand">
            <span className="auth-brand-mark">
              <Leaf size={22} strokeWidth={2.2} />
            </span>

            <div>
              <strong>{t('brand.name')}</strong>
              <small>{t('brand.tagline')}</small>
            </div>
          </div>

          <span className="auth-secure-pill">
            <ShieldCheck size={15} />
            {t('auth.secure')}
          </span>
        </header>

        <div className="auth-story-layout">
          <div className="auth-story-copy">
            <span className="auth-kicker">
              <Leaf size={15} />
              {t('auth.kicker')}
            </span>

            <h1>{t('auth.storyTitle')}</h1>

            <p>{t('auth.storyText')}</p>

            <div className="auth-benefit-list">
              <article>
                <BadgeCheck size={19} />

                <div>
                  <strong>{t('auth.benefit1')}</strong>
                  <span>{t('auth.benefit1Text')}</span>
                </div>
              </article>

              <article>
                <BadgeCheck size={19} />

                <div>
                  <strong>{t('auth.benefit2')}</strong>
                  <span>{t('auth.benefit2Text')}</span>
                </div>
              </article>

              <article>
                <BadgeCheck size={19} />

                <div>
                  <strong>{t('auth.benefit3')}</strong>
                  <span>{t('auth.benefit3Text')}</span>
                </div>
              </article>
            </div>
          </div>

          <div
            className="auth-mascot-stage"
            aria-label={t('auth.mascotAlt')}
          >
            <div className="auth-mascot-shadow" />

            <img
              src="/brand/tuber-mitra.png"
              alt={t('auth.mascotAlt')}
              className="auth-mascot"
            />

            <div className="auth-mascot-message">
              <span>{t('auth.mascotGreeting')}</span>
              <strong>{t('auth.mascotMessage')}</strong>
            </div>
          </div>
        </div>

        <footer className="auth-visual-footer">
          <span>{t('auth.footerLine')}</span>

          <span className="auth-live-dot">
            <i />
            {t('auth.systemReady')}
          </span>
        </footer>
      </section>

      <section className="auth-form-panel">
        <div className="auth-mobile-brand">
          <span className="auth-brand-mark">
            <Leaf size={21} />
          </span>

          <strong>{t('brand.name')}</strong>
        </div>

        <button
          type="button"
          className="auth-language-button"
          onClick={() =>
            setLanguage(language === 'en' ? 'kn' : 'en')
          }
        >
          <Languages size={17} />

          <span>
            {language === 'en' ? 'ಕನ್ನಡ' : 'English'}
          </span>
        </button>

        <div className="auth-form-wrap">
          <div
            className="auth-progress"
            aria-label={t('auth.progressLabel')}
          >
            <span className="active" />
            <span className={step === 'otp' ? 'active' : ''} />
          </div>

          <div className="auth-form-heading">
            <span className="auth-form-icon">
              {step === 'phone' ? (
                <Phone size={22} />
              ) : (
                <MessageSquareText size={22} />
              )}
            </span>

            <span className="auth-step-label">
              {step === 'phone'
                ? t('auth.step1')
                : t('auth.step2')}
            </span>

            <h2>
              {step === 'phone'
                ? t('auth.title')
                : t('auth.verifyTitle')}
            </h2>

            <p>
              {step === 'phone'
                ? t('auth.subtitle')
                : t('auth.verifyText', {
                    phone: maskedPhone,
                  })}
            </p>
          </div>

          {step === 'phone' ? (
            <form
              onSubmit={requestOtp}
              className="auth-form"
            >
              <label
                className="auth-field-label"
                htmlFor="mobile-number"
              >
                {t('auth.mobile')}
              </label>

              <div className="auth-phone-input">
                <span>
                  <small>IN</small>
                  <strong>+91</strong>
                </span>

                <input
                  id="mobile-number"
                  inputMode="numeric"
                  autoComplete="tel-national"
                  maxLength={10}
                  value={phone}
                  onChange={(event) =>
                    setPhone(
                      event.target.value
                        .replace(/\D/g, '')
                        .slice(0, 10),
                    )
                  }
                  placeholder="98765 43210"
                  aria-describedby="mobile-help"
                  autoFocus
                />
              </div>

              <small
                id="mobile-help"
                className="auth-field-help"
              >
                {t('auth.mobileHelp')}
              </small>

              {error && (
                <div
                  className="auth-error"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <button
                className="auth-submit"
                type="submit"
                disabled={loading || phone.length !== 10}
              >
                <span>
                  {loading
                    ? t('auth.sending')
                    : t('auth.sendOtp')}
                </span>

                <ArrowRight size={18} />
              </button>

              {mode === 'supabase' && (
                <>
                  <div className="auth-divider">
                    <span>or</span>
                  </div>

                  <button
                    type="button"
                    className="auth-google-button"
                    disabled={loading}
                    onClick={handleGoogleSignIn}
                  >
                    <svg
                      className="auth-google-icon"
                      viewBox="0 0 24 24"
                      width="19"
                      height="19"
                      aria-hidden="true"
                    >
                      <path
                        fill="#4285F4"
                        d="M21.6 12.23c0-.71-.06-1.4-.18-2.07H12v3.92h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.9-1.75 2.98-4.33 2.98-7.38Z"
                      />
                      <path
                        fill="#34A853"
                        d="M12 22c2.7 0 4.97-.9 6.63-2.39l-3.24-2.51c-.9.6-2.05.96-3.39.96-2.61 0-4.82-1.76-5.61-4.13H3.04v2.59A10 10 0 0 0 12 22Z"
                      />
                      <path
                        fill="#FBBC05"
                        d="M6.39 13.93A6.02 6.02 0 0 1 6.08 12c0-.67.11-1.32.31-1.93V7.48H3.04A10 10 0 0 0 2 12c0 1.61.38 3.14 1.04 4.52l3.35-2.59Z"
                      />
                      <path
                        fill="#EA4335"
                        d="M12 5.94c1.47 0 2.79.51 3.83 1.5l2.87-2.87A9.62 9.62 0 0 0 12 2 10 10 0 0 0 3.04 7.48l3.35 2.59C7.18 7.7 9.39 5.94 12 5.94Z"
                      />
                    </svg>

                    <span>
                      Continue with Google
                    </span>
                  </button>
                </>
              )}
            </form>
          ) : (
            <form
              onSubmit={confirmOtp}
              className="auth-form"
            >
              <div className="auth-otp-header">
                <label className="auth-field-label">
                  {t('auth.otp')}
                </label>

                <button
                  type="button"
                  className="auth-change-number"
                  onClick={() => {
                    setStep('phone')
                    setOtpDigits(
                      Array(OTP_LENGTH).fill(''),
                    )
                    setError('')
                  }}
                >
                  <ArrowLeft size={14} />
                  {t('auth.changeNumber')}
                </button>
              </div>

              <div
                className="auth-otp-grid"
                onPaste={handleOtpPaste}
              >
                {otpDigits.map((digit, index) => (
                  <input
                    key={index}
                    ref={(node) => {
                      otpRefs.current[index] = node
                    }}
                    type="text"
                    inputMode="numeric"
                    autoComplete={
                      index === 0
                        ? 'one-time-code'
                        : 'off'
                    }
                    maxLength={1}
                    value={digit}
                    onChange={(event) =>
                      updateOtpDigit(
                        index,
                        event.target.value,
                      )
                    }
                    onKeyDown={(event) =>
                      handleOtpKeyDown(index, event)
                    }
                    aria-label={`${t(
                      'auth.otpDigit',
                    )} ${index + 1}`}
                  />
                ))}
              </div>

              {mode === 'demo' && (
                <div className="auth-demo-code">
                  <LockKeyhole size={16} />

                  <span>
                    {t('auth.demoCode')}{' '}
                    <strong>123456</strong>
                  </span>
                </div>
              )}

              {error && (
                <div
                  className="auth-error"
                  role="alert"
                >
                  {error}
                </div>
              )}

              <button
                className="auth-submit"
                type="submit"
                disabled={loading || !otpComplete}
              >
                <span>
                  {loading
                    ? t('auth.verifying')
                    : t('auth.verify')}
                </span>

                <ArrowRight size={18} />
              </button>

              <div className="auth-resend-row">
                <span>{t('auth.notReceived')}</span>

                <button
                  type="button"
                  disabled={
                    seconds > 0 || loading
                  }
                  onClick={() => requestOtp()}
                >
                  {seconds > 0
                    ? t('auth.resendIn', {
                        seconds,
                      })
                    : t('auth.resend')}
                </button>
              </div>
            </form>
          )}

          <div className="auth-trust-row">
            <ShieldCheck size={16} />
            <span>{t('auth.privacy')}</span>
          </div>

          <p className="auth-terms">
            {t('auth.terms')}
          </p>
        </div>
      </section>
    </main>
  )
}