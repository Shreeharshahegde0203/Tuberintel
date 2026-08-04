import type { Language } from '../i18n/I18nContext'

const localeFor = (language: Language = 'en') => language === 'kn' ? 'kn-IN' : 'en-IN'

export const formatCurrency = (value: number, maximumFractionDigits = 0, language: Language = 'en') =>
  new Intl.NumberFormat(localeFor(language), {
    style: 'currency',
    currency: 'INR',
    maximumFractionDigits,
  }).format(value)

export const formatNumber = (value: number, digits = 1, language: Language = 'en') =>
  new Intl.NumberFormat(localeFor(language), { maximumFractionDigits: digits }).format(value)

export const formatDate = (value: string | Date, language: Language = 'en') =>
  new Intl.DateTimeFormat(localeFor(language), {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
  }).format(new Date(value))

export const actionLabel = (action?: string | null, language: Language = 'en') => {
  const maps: Record<Language, Record<string, string>> = {
    en: { SELL_NOW: 'Sell now', STORE: 'Store', PROCESS: 'Process', WAIT: 'Wait' },
    kn: { SELL_NOW: 'ಈಗಲೇ ಮಾರಾಟ ಮಾಡಿ', STORE: 'ಸಂಗ್ರಹಿಸಿ', PROCESS: 'ಸಂಸ್ಕರಣೆಗೆ ನೀಡಿ', WAIT: 'ಕಾಯಿರಿ' },
  }
  return action ? maps[language][action] || action : language === 'kn' ? 'ಬಾಕಿ ಇದೆ' : 'Pending'
}
