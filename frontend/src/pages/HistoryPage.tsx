import { ArrowRight, Search, ScanLine } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusBadge } from '../components/Common'
import { useI18n } from '../i18n/I18nContext'
import { getBatches } from '../services/api'
import { actionLabel, formatCurrency, formatDate, formatNumber } from '../services/format'
import type { BatchListItem } from '../types'

export default function HistoryPage() {
  const [items, setItems] = useState<BatchListItem[] | null>(null)
  const [query, setQuery] = useState('')
  const [error, setError] = useState('')
  const { language, t } = useI18n()
  const load = () => getBatches().then(setItems).catch((err) => setError(err?.response?.data?.detail || err.message))
  useEffect(() => { void load() }, [])

  const filtered = useMemo(() => (items || []).filter((item) => `${item.batch_code} ${item.variety} ${item.source_location}`.toLowerCase().includes(query.toLowerCase())), [items, query])
  if (error) return <ErrorState message={String(error)} retry={load} />
  if (!items) return <LoadingState />

  const searchPlaceholder = language === 'kn' ? 'ಲಾಟ್, ತಳಿ ಅಥವಾ ಸ್ಥಳ ಹುಡುಕಿ' : 'Search batch, variety or location'
  return <>
    <PageHeader eyebrow={t('history.eyebrow')} title={t('history.title')} description={t('history.description')} actions={<Link className="button button-primary" to="/analyze"><ScanLine size={19} /> {t('top.newInspection')}</Link>} />
    <section className="panel table-panel">
      <div className="table-toolbar"><div className="search-field"><Search size={20} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={searchPlaceholder} /></div><span>{filtered.length} {language === 'kn' ? 'ದಾಖಲೆಗಳು' : 'records'}</span></div>
      {filtered.length === 0 ? <EmptyState title={language === 'kn' ? 'ಹೊಂದುವ ಲಾಟ್‌ಗಳಿಲ್ಲ' : 'No matching batches'} description={language === 'kn' ? 'ಹುಡುಕಾಟವನ್ನು ಬದಲಿಸಿ ಅಥವಾ ಹೊಸ ಲಾಟ್ ನೋಂದಾಯಿಸಿ.' : 'Change the search text or register a new potato batch.'} actionLabel={t('top.newInspection')} actionTo="/analyze" /> : <div className="table-scroll"><table><thead><tr><th>{t('table.batch')}</th><th>{t('table.origin')}</th><th>{t('table.quantity')}</th><th>{language === 'kn' ? 'ಸ್ಥಿತಿ' : 'Status'}</th><th>{t('table.quality')}</th><th>{language === 'kn' ? 'ಶಿಫಾರಸು' : 'Recommendation'}</th><th>{t('table.profit')}</th><th /></tr></thead><tbody>{filtered.map((batch) => <tr key={batch.id}><td><strong>{batch.batch_code}</strong><span className="cell-subtitle">{batch.variety} · {formatDate(batch.created_at, language)}</span></td><td>{batch.source_location}</td><td>{formatNumber(batch.quantity_kg, 0, language)} kg</td><td><StatusBadge value={batch.status} /></td><td>{batch.grade ? <div className="quality-cell"><span className={`grade-token grade-${batch.grade.toLowerCase()}`}>{batch.grade}</span><span>{batch.quality_score?.toFixed(1)}</span></div> : '—'}</td><td><StatusBadge value={batch.action ? actionLabel(batch.action, language) : t('common.pending')} /></td><td>{batch.expected_net_profit == null ? '—' : formatCurrency(batch.expected_net_profit, 0, language)}</td><td><Link className="row-link" to={`/batches/${batch.id}`}><ArrowRight size={20} /></Link></td></tr>)}</tbody></table></div>}
    </section>
  </>
}
