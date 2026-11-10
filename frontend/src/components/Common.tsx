import type { LucideIcon } from 'lucide-react'
import { AlertTriangle, ArrowRight, Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { useI18n } from '../i18n/I18nContext'

export function PageHeader({ eyebrow, title, description, actions }: { eyebrow?: string; title: string; description?: string; actions?: ReactNode }) {
  return <div className="page-header"><div>{eyebrow && <span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{description && <p>{description}</p>}</div>{actions && <div className="page-header-actions">{actions}</div>}</div>
}

export function StatCard({ icon: Icon, label, value, detail, tone = 'default' }: { icon: LucideIcon; label: string; value: string; detail: string; tone?: 'default' | 'positive' | 'warning' }) {
  return <article className={`stat-card tone-${tone}`}><div className="stat-icon"><Icon size={22} /></div><div className="stat-label">{label}</div><div className="stat-value">{value}</div><div className="stat-detail">{detail}</div></article>
}

export function StatusBadge({ value }: { value: string | null | undefined }) {
  const { t } = useI18n()
  const normalized = (value || 'pending').toLowerCase().replaceAll('_', '-')
  const statusKey = `status.${normalized}`
  const translated = t(statusKey)
  const label = !value ? t('common.pending') : translated === statusKey ? value.replaceAll('_', ' ') : translated
  return <span className={`status-badge status-${normalized}`}>{label}</span>
}

export function LoadingState({ label }: { label?: string }) {
  const { t } = useI18n()
  return <div className="state-panel"><Loader2 className="spin" size={28} /><p>{label || t('common.loading')}</p></div>
}

export function ErrorState({ message, retry }: { message: string; retry?: () => void }) {
  const { t } = useI18n()
  return <div className="state-panel state-error"><AlertTriangle size={28} /><strong>{t('common.unable')}</strong><p>{message}</p>{retry && <button className="button button-secondary" onClick={retry}>{t('common.retry')}</button>}</div>
}

export function EmptyState({ title, description, actionLabel, actionTo }: { title: string; description: string; actionLabel?: string; actionTo?: string }) {
  return <div className="empty-state"><div className="empty-mark"><LeafMini /></div><strong>{title}</strong><p>{description}</p>{actionLabel && actionTo && <Link className="button button-primary" to={actionTo}>{actionLabel}<ArrowRight size={19} /></Link>}</div>
}

function LeafMini() {
  return <svg width="34" height="34" viewBox="0 0 30 30" fill="none" aria-hidden="true"><path d="M24.5 5.7C17.4 6 10.1 9.1 7.8 15.4c-1.6 4.4.7 7.8 4.9 7.8 6.8 0 10.9-8 11.8-17.5Z" stroke="currentColor" strokeWidth="1.8" /><path d="M6.2 25.2c3.1-6.1 7.9-10.7 14.4-14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg>
}

export function MetricBar({ label, value, inverse = false }: { label: string; value: number; inverse?: boolean }) {
  const safe = Math.max(0, Math.min(100, value))
  const level = inverse ? 100 - safe : safe
  return <div className="metric-bar-row"><div className="metric-bar-label"><span>{label}</span><strong>{safe.toFixed(1)}</strong></div><div className="metric-track"><span style={{ width: `${safe}%` }} data-level={level < 45 ? 'low' : level < 75 ? 'medium' : 'high'} /></div></div>
}
