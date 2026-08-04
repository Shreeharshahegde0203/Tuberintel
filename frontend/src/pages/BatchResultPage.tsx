import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Download,
  IndianRupee,
  MapPin,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ErrorState, LoadingState, MetricBar, PageHeader, StatusBadge } from '../components/Common'
import { getBatch, mediaBase, submitFeedback } from '../services/api'
import { useI18n } from '../i18n/I18nContext'
import { actionLabel, formatCurrency, formatDate, formatNumber } from '../services/format'
import type { Batch } from '../types'

const actionTone: Record<string, string> = {
  SELL_NOW: 'sell',
  STORE: 'store',
  PROCESS: 'process',
  WAIT: 'wait',
}

export default function BatchResultPage() {
  const { batchId } = useParams()
  const [batch, setBatch] = useState<Batch | null>(null)
  const [error, setError] = useState('')
  const [feedbackStatus, setFeedbackStatus] = useState('')
  const { language, t } = useI18n()
  const [feedback, setFeedback] = useState({ action_taken: '', actual_price_per_quintal: '', actual_profit: '', rating: '5', notes: '' })

  const load = () => {
    if (!batchId) return
    setError('')
    getBatch(Number(batchId)).then(setBatch).catch((err) => setError(err?.response?.data?.detail || err.message))
  }

  useEffect(load, [batchId])

  const comparison = useMemo(() => batch?.recommendation?.alternatives.map((item) => ({
    name: actionLabel(item.action, language),
    profit: item.net_profit,
    risk: item.risk_score,
  })) || [], [batch, language])

  const costLabel = (key: string) => {
    const translated = t(`cost.${key}`)
    return translated.startsWith('cost.') ? key.replaceAll('_', ' ') : translated
  }

  if (error) return <ErrorState message={String(error)} retry={load} />
  if (!batch) return <LoadingState />
  if (!batch.assessment || !batch.recommendation) {
    return (
      <div>
        <PageHeader title={batch.batch_code} description={t('result.notComplete')} />
        <div className="panel state-panel"><AlertTriangle /><p>{t('result.uploadFirst')}</p><Link className="button button-primary" to="/analyze">{t('result.startInspection')}</Link></div>
      </div>
    )
  }

  const assessment = batch.assessment
  const rec = batch.recommendation
  const topImage = batch.images.find((img) => img.annotated_url) || batch.images[0]
  const imageSrc = topImage?.annotated_url ? `${mediaBase}${topImage.annotated_url}` : topImage?.image_url ? `${mediaBase}${topImage.image_url}` : null
  const imagesAnalyzed =
    typeof assessment.feature_summary.images_analyzed === 'number'
      ? assessment.feature_summary.images_analyzed
      : batch.images.length
  const potatoesDetected =
    typeof assessment.feature_summary.potatoes_detected === 'number'
      ? assessment.feature_summary.potatoes_detected
      : '—'

  const defects = [
    [t('defect.bruising'), assessment.bruise_severity],
    [t('defect.scab'), assessment.scab_severity],
    [t('defect.cracks'), assessment.crack_severity],
    [t('defect.discoloration'), assessment.discoloration_severity],
    [t('defect.deformity'), assessment.deformity_severity],
    [t('defect.sprouting'), assessment.sprout_severity],
  ] as const

  const saveFeedback = async (event: FormEvent) => {
    event.preventDefault()
    setFeedbackStatus(language === 'kn' ? 'ಫಲಿತಾಂಶ ಉಳಿಸಲಾಗುತ್ತಿದೆ…' : 'Saving outcome…')
    try {
      await submitFeedback(batch.id, {
        action_taken: feedback.action_taken || rec.recommended_action,
        actual_price_per_quintal: feedback.actual_price_per_quintal ? Number(feedback.actual_price_per_quintal) : null,
        actual_profit: feedback.actual_profit ? Number(feedback.actual_profit) : null,
        rating: Number(feedback.rating),
        notes: feedback.notes,
      })
      setFeedbackStatus(language === 'kn' ? 'ಶಿಫಾರಸು ಪರಿಶೀಲನೆಗಾಗಿ ಫಲಿತಾಂಶ ಉಳಿಸಲಾಗಿದೆ.' : 'Outcome saved for recommendation validation.')
    } catch (err: any) {
      setFeedbackStatus(err?.response?.data?.detail || (language === 'kn' ? 'ಫಲಿತಾಂಶ ಉಳಿಸಲು ಸಾಧ್ಯವಾಗಲಿಲ್ಲ.' : 'Could not save the outcome.'))
    }
  }

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(batch, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `${batch.batch_code}-analysis.json`
    anchor.click()
    URL.revokeObjectURL(url)
  }

  return (
    <>
      <PageHeader
        eyebrow={t('result.completed')}
        title={batch.batch_code}
        description={`${batch.variety} · ${formatNumber(batch.quantity_kg, 0, language)} kg · ${batch.source_location}`}
        actions={<div className="button-row"><Link className="button button-secondary" to="/history"><ArrowLeft size={19} /> {t('common.history')}</Link><button className="button button-secondary" onClick={downloadJson}><Download size={19} /> {t('common.exportJson')}</button></div>}
      />

      <section className={`recommendation-hero action-${actionTone[rec.recommended_action] || 'sell'}`}>
        <div className="recommendation-main">
          <span className="recommendation-label"><Sparkles size={16} /> {t('result.recommended')}</span>
          <h2>{actionLabel(rec.recommended_action, language)}</h2>
          <p>{rec.explanation[0]}</p>
          <div className="recommendation-meta">
            <span><MapPin size={17} /> {rec.recommended_market}</span>
            <span><Clock3 size={17} /> {rec.recommended_timing}</span>
            <span><ShieldCheck size={17} /> {rec.confidence.toFixed(0)}% {t('result.confidence')}</span>
          </div>
        </div>
        <div className="recommendation-value">
          <span>{t('result.expectedProfit')}</span>
          <strong>{formatCurrency(rec.expected_net_profit, 0, language)}</strong>
          <small>{formatCurrency(rec.expected_selling_price, 0, language)} {t('result.perQuintal')} · {t('result.roi')} {rec.expected_roi.toFixed(1)}%</small>
        </div>
      </section>

      <section className="result-grid">
        <article className="panel result-image-panel span-7">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.cvInspection')}</span><h2>{t('result.surfaceAssessment')}</h2></div><StatusBadge value={`Grade ${assessment.quality_grade}`} /></div>
          {imageSrc ? <img className="result-image" src={imageSrc} alt={language === 'kn' ? 'ಗುರುತಿಸಲಾದ ಆಲೂಗಡ್ಡೆ ಪರಿಶೀಲನೆ' : 'Annotated potato inspection'} /> : <div className="image-missing">{t('result.noImage')}</div>}
          <div className="image-legend"><span className="legend-red" /> {t('result.legendBruise')} <span className="legend-green" /> {t('result.legendScab')} <span className="legend-blue" /> {t('result.legendCrack')} <span className="legend-amber" /> {t('result.legendGreen')}</div>
          <p className="explainability-caption">{String(assessment.feature_summary.explainability_mode || 'Transparent feature overlays')}</p>
        </article>

        <article className="panel span-5 quality-summary-panel">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.batchGrade')}</span><h2>{t('result.multiQuality')}</h2></div></div>
          <div className="quality-score-block">
            <div className={`grade-seal grade-${assessment.quality_grade.toLowerCase()}`}>{assessment.quality_grade}</div>
            <div><strong>{assessment.quality_score.toFixed(1)}</strong><span>{t('result.qualityScore')}</span><small>{assessment.commercial_class}</small></div>
          </div>
          <MetricBar label={t('result.sizeUniformity')} value={assessment.size_uniformity} />
          <MetricBar label={t('result.surfaceIntegrity')} value={100 - assessment.surface_defect_severity} />
          <MetricBar label={t('result.modelConfidence')} value={assessment.confidence} />
          <div className="quality-risk-strip">
            <div><span>{t('result.rejection')}</span><strong>{assessment.rejection_probability.toFixed(1)}%</strong></div>
            <div><span>{t('result.storageSensitivity')}</span><strong>{Math.min(100, (assessment.sprout_severity + assessment.bruise_severity + assessment.discoloration_severity) / 3).toFixed(1)}</strong></div>
          </div>
        </article>
      </section>

      <section className="result-grid">
        <article className="panel span-5">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.defectProfile')}</span><h2>{t('result.severity')}</h2></div></div>
          <div className="metric-list">
            {defects.map(([label, value]) => <MetricBar key={label} label={label} value={value} inverse />)}
          </div>
        </article>

        <article className="panel span-7 chart-panel compact-chart">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.pathComparison')}</span><h2>{t('result.riskAlternatives')}</h2></div></div>
          <div className="chart-wrap">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={comparison} margin={{ left: -10, right: 10 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} />
                <XAxis dataKey="name" axisLine={false} tickLine={false} />
                <YAxis axisLine={false} tickLine={false} tickFormatter={(v) => `₹${Math.round(v / 1000)}k`} />
                <Tooltip formatter={(value) => formatCurrency(Number(value), 0, language)} />
                <Bar dataKey="profit" fill="var(--green-700)" radius={[5, 5, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </article>
      </section>

      <section className="result-grid">
        <article className="panel span-7">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.explainable')}</span><h2>{t('result.why')}</h2></div></div>
          <ol className="reason-list">
            {rec.explanation.map((reason, index) => <li key={index}><span>{index + 1}</span><p>{reason}</p></li>)}
          </ol>
        </article>

        <article className="panel span-5">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.financial')}</span><h2>{t('result.realization')}</h2></div></div>
          <div className="financial-summary">
            <div><span>{t('result.gross')}</span><strong>{formatCurrency(rec.expected_gross_revenue, 0, language)}</strong></div>
            {Object.entries(rec.cost_breakdown).map(([key, value]) => <div key={key}><span>{costLabel(key)}</span><strong>- {formatCurrency(value, 0, language)}</strong></div>)}
            <div className="financial-total"><span>{t('result.expectedProfit')}</span><strong>{formatCurrency(rec.expected_net_profit, 0, language)}</strong></div>
          </div>
          <div className="advisory-note"><IndianRupee size={18} /><p>{t('result.advisory')}</p></div>
        </article>
      </section>

      <section className="result-grid">
        <article className="panel span-7">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.decomposition')}</span><h2>{t('result.contributions')}</h2></div></div>
          <div className="factor-list">
            {rec.decision_factors?.map((factor) => (
              <div className="factor-row" key={factor.factor}>
                <div><strong>{factor.factor}</strong><p>{factor.explanation}</p></div>
                <span className={factor.direction === 'positive' ? 'factor-positive' : 'factor-negative'}>{factor.contribution >= 0 ? '+' : ''}{formatCurrency(factor.contribution, 0, language)}</span>
              </div>
            ))}
          </div>
        </article>
        <article className="panel span-5">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.continuous')}</span><h2>{t('result.feedback')}</h2></div></div>
          <form className="feedback-form" onSubmit={saveFeedback}>
            <label>{t('feedback.action')}<select value={feedback.action_taken} onChange={(e) => setFeedback({ ...feedback, action_taken: e.target.value })}><option value="">{t('feedback.useRecommended')}</option><option value="SELL_NOW">{t('feedback.soldNow')}</option><option value="STORE">{t('feedback.stored')}</option><option value="PROCESS">{t('feedback.processed')}</option><option value="WAIT">{t('feedback.delayed')}</option></select></label>
            <div className="form-grid-two"><label>{t('feedback.actualPrice')}<input type="number" min="0" value={feedback.actual_price_per_quintal} onChange={(e) => setFeedback({ ...feedback, actual_price_per_quintal: e.target.value })} /></label><label>{t('feedback.actualProfit')}<input type="number" value={feedback.actual_profit} onChange={(e) => setFeedback({ ...feedback, actual_profit: e.target.value })} /></label></div>
            <label>{t('feedback.rating')}<select value={feedback.rating} onChange={(e) => setFeedback({ ...feedback, rating: e.target.value })}>{[5,4,3,2,1].map((value) => <option key={value} value={value}>{value} / 5</option>)}</select></label>
            <label>{t('feedback.notes')}<textarea rows={3} value={feedback.notes} onChange={(e) => setFeedback({ ...feedback, notes: e.target.value })} placeholder={t('feedback.placeholder')} /></label>
            <button className="button button-primary" type="submit"><CheckCircle2 size={17} /> {t('feedback.save')}</button>
            {feedbackStatus && <p className="form-status">{feedbackStatus}</p>}
          </form>
        </article>
      </section>

      <section className="panel alternatives-panel">
        <div className="panel-heading"><div><span className="panel-kicker">{t('result.allOptions')}</span><h2>{t('result.decisionRanking')}</h2></div></div>
        <div className="alternative-grid">
          {rec.alternatives.map((alt, index) => (
            <article key={alt.action} className={index === 0 ? 'best-alternative' : ''}>
              <div className="alternative-top"><span>{index + 1}</span><StatusBadge value={actionLabel(alt.action, language)} /></div>
              <h3>{alt.title}</h3>
              <p>{alt.market}</p>
              <div className="alternative-profit">{formatCurrency(alt.net_profit, 0, language)}</div>
              <div className="alternative-stats"><span><TrendingUp size={15} /> {t('result.roi')} {alt.roi.toFixed(1)}%</span><span><ShieldCheck size={15} /> {t('result.risk')} {alt.risk_score.toFixed(0)}</span></div>
            </article>
          ))}
        </div>
      </section>

      <footer className="result-footer">{t('result.analysisGenerated')} {formatDate(batch.updated_at, language)} · {imagesAnalyzed} {t('result.images')} · {potatoesDetected} {t('result.potatoRegions')}</footer>
    </>
  )
}
