import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  Clock3,
  Download,
  IndianRupee,
  MapPin,
  ShieldCheck,
  TrendingUp,
} from 'lucide-react'
import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
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

  const load = useCallback((signal?: AbortSignal) => {
    if (!batchId) return
    setError('')
    getBatch(Number(batchId), signal)
      .then((result) => { if (!signal?.aborted) setBatch(result) })
      .catch((err) => { if (!signal?.aborted) setError(err?.response?.data?.detail || err.message) })
  }, [batchId])

  useEffect(() => {
    const controller = new AbortController()
    load(controller.signal)
    return () => controller.abort()
  }, [load])

  const comparison = useMemo(() => batch?.recommendation?.alternatives.filter((item) => item.eligible !== false).map((item) => ({
    name: actionLabel(item.action, language),
    profit: item.net_profit,
    risk: item.risk_score,
  })) || [], [batch, language])

  const costLabel = (key: string) => {
    const translated = t(`cost.${key}`)
    return translated.startsWith('cost.') ? key.replaceAll('_', ' ') : translated
  }

  if (error) return <ErrorState message={String(error)} retry={() => load()} />
  if (!batch || String(batch.id) !== batchId) return <LoadingState />
  if (batch.status !== 'analyzed' || !batch.assessment || !batch.recommendation) {
    return (
      <div>
        <PageHeader title={batch.batch_code} description={t('result.notComplete')} />
        <div className="panel state-panel"><AlertTriangle /><p>{t('result.uploadFirst')}</p><Link className="button button-primary" to="/analyze">{t('result.startInspection')}</Link></div>
      </div>
    )
  }

  const assessment = batch.assessment
  const rec = batch.recommendation
  const summary = assessment.feature_summary || {}

  const conditionDistribution =
    summary.condition_distribution || {}

  const visionDefects =
    summary.defect_area_percent || {}

  const visionActive =
    Number(summary.vision_v1_images || 0) > 0

  const manualReviewRequired =
    Boolean(summary.manual_review_required)

  const reviewReasons =
    Array.isArray(summary.review_reasons)
      ? summary.review_reasons.map(String)
      : []

  const independentImages =
    Number(
      summary.independent_images
      || summary.images_analyzed
      || batch.images.length
    )

  const duplicatesIgnored =
    Number(summary.duplicate_images_ignored || 0)

  const topCondition =
    typeof summary.top_condition === 'string'
      ? summary.top_condition
      : null

  const conditionRows = [
    ['Healthy', Number(conditionDistribution.Healthy || 0)],
    ['Damaged', Number(conditionDistribution.Damaged || 0)],
    ['Defected', Number(conditionDistribution.Defected || 0)],
    ['Diseased-Fungal', Number(conditionDistribution['Diseased-Fungal'] || 0)],
    ['Sprouted', Number(conditionDistribution.Sprouted || 0)],
  ] as const

  const visionDefectRows = [
    ['Scab', Number(visionDefects.scab || 0)],
    ['Rot', Number(visionDefects.rot || 0)],
    ['Greening', Number(visionDefects.greening || 0)],
    ['Mechanical damage', Number(visionDefects.mechanical_damage || 0)],
  ] as const

  const totalVisibleDefect =
    Number(visionDefects.total_visible_defect || 0)

  const topImage = batch.images.find((img) => img.annotated_url) || batch.images[0]
  const imageSrc = topImage?.annotated_url ? `${mediaBase}${topImage.annotated_url}` : topImage?.image_url ? `${mediaBase}${topImage.image_url}` : null

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

  const marketSnapshot = assessment.feature_summary.market_snapshot as {
    analyzed_at: string; reporting_date: string | null; status: 'recent' | 'stale' | 'unavailable';
  } | undefined
  const hasRecommendation = rec.alternatives.some((option) => option.eligible !== false)

  const qualityValuation = assessment.feature_summary.quality_valuation as {
    reference_price_per_quintal: number; effective_value_per_original_kg: number;
    applied_factor: number; accepted_weight_factor: number; status: string;
    sampling_basis: string; calibration_status: string;
  } | undefined

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

      <section className="panel form-section">
        <h2>Market data at inspection</h2>
        {marketSnapshot ? <p>
          {marketSnapshot.status === 'recent' && `Mandi reporting date: ${marketSnapshot.reporting_date}.`}
          {marketSnapshot.status === 'stale' && `Mandi report from ${marketSnapshot.reporting_date} was too old to use.`}
          {marketSnapshot.status === 'unavailable' && 'No usable mandi report was available for the selected market and variety.'}
          {' '}Run a new inspection for updated pricing.
        </p> : <p>This saved inspection has no recorded market freshness. Run a new inspection for updated pricing.</p>}
      </section>

      {hasRecommendation ? <section className={`recommendation-hero action-${actionTone[rec.recommended_action] || 'sell'}`}>
        <div className="recommendation-main">
          <span className="recommendation-label"><CheckCircle2 size={16} /> {t('result.recommended')}</span>
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

      : <section className="panel form-section"><h2>Pricing inputs needed</h2><p>Provide a current buyer quote or select a market with a recent report.</p></section>}

      {/* TUBERINTEL QUALITY VALUE V1 */}
      {hasRecommendation && qualityValuation && <section className="panel form-section">
        <div className="panel-heading"><div><span className="panel-kicker">{qualityValuation.status}</span><h2>{language === 'kn' ? 'ಗುಣಮಟ್ಟ ಆಧಾರಿತ ಬ್ಯಾಚ್ ಮೌಲ್ಯ' : 'Quality-adjusted batch value'}</h2></div></div>
        <div className="form-grid two-col">
          <p>{language === 'kn' ? 'ಉಲ್ಲೇಖ / quote ದರ' : 'Reference / quoted price'}: <strong>{formatCurrency(qualityValuation.reference_price_per_quintal / 100, 2, language)}/kg</strong></p>
          <p>{language === 'kn' ? 'ಮೂಲ ಬ್ಯಾಚ್ kg ಗೆ ಅಂದಾಜು ಮೌಲ್ಯ' : 'Projected value per original batch kg'}: <strong>{formatCurrency(qualityValuation.effective_value_per_original_kg, 2, language)}/kg</strong></p>
          <p>Applied value factor: <strong>{(qualityValuation.applied_factor * 100).toFixed(1)}%</strong></p>
          <p>Retained weight assumption: <strong>{(qualityValuation.accepted_weight_factor * 100).toFixed(1)}%</strong></p>
        </div>
        <p className="fine-print">{qualityValuation.calibration_status === 'uncalibrated_scenario' ? 'Prototype scenario, not a verified buyer price. ' : ''}{qualityValuation.sampling_basis}. Value per original kg includes any entered sorting loss; it is not the price per accepted kg. Storage loss and explicit costs are accounted for separately.</p>
      </section>}

      <section className="result-grid">
        <article className="panel result-image-panel span-7">
          <div className="panel-heading"><div><span className="panel-kicker">{t('result.cvInspection')}</span><h2>{t('result.surfaceAssessment')}</h2></div><StatusBadge value={`Grade ${assessment.quality_grade}`} /></div>
          {imageSrc ? <img className="result-image" src={imageSrc} alt={language === 'kn' ? 'ಗುರುತಿಸಲಾದ ಆಲೂಗಡ್ಡೆ ಪರಿಶೀಲನೆ' : 'Annotated potato inspection'} /> : <div className="image-missing">{t('result.noImage')}</div>}
          {visionActive ? (
            <div className="image-legend">
              <span className="legend-roi" /> Potato ROI
              <span className="legend-scab-v1" /> Scab
              <span className="legend-rot-v1" /> Rot
              <span className="legend-green-v1" /> Greening
              <span className="legend-mechanical-v1" /> Mechanical damage
            </div>
          ) : (
            <div className="image-legend">
              <span className="legend-red" /> {t('result.legendBruise')}
              <span className="legend-green" /> {t('result.legendScab')}
              <span className="legend-blue" /> {t('result.legendCrack')}
              <span className="legend-amber" /> {t('result.legendGreen')}
            </div>
          )}
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

      {manualReviewRequired && (
        <section className="vision-review-banner">
          <AlertTriangle size={22} />
          <div>
            <strong>Manual review recommended</strong>

            {reviewReasons.length > 0 ? (
              <ul>
                {reviewReasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <p>
                Review model confidence and cross-image evidence
                before acting.
              </p>
            )}
          </div>
        </section>
      )}

      <section className="panel vision-evidence-panel">
        <div className="panel-heading vision-evidence-heading">
          <div>
            <span className="panel-kicker">
              TuberIntel Vision v1
            </span>
            <h2>Learned vision evidence</h2>
          </div>

          <StatusBadge
            value={
              visionActive
                ? 'Vision v1 active'
                : 'CV fallback'
            }
          />
        </div>

        {visionActive ? (
          <>
            <div className="vision-stage-grid">

              <article className="vision-stage-card">
                <div className="vision-stage-top">
                  <span>A</span>
                  <small>YOLO11n-Seg</small>
                </div>

                <h3>Potato ROI segmentation</h3>

                <strong className="vision-stage-value">
                  {summary.potatoes_detected ?? '?'}
                </strong>

                <p>
                  Detected potato regions across independent
                  uploaded views.
                </p>
              </article>

              <article className="vision-stage-card">
                <div className="vision-stage-top">
                  <span>B</span>
                  <small>YOLO11s-Cls</small>
                </div>

                <h3>Condition classification</h3>

                {topCondition && (
                  <div className="vision-top-condition">
                    <span>Dominant condition</span>
                    <strong>{topCondition}</strong>
                  </div>
                )}

                <div className="vision-breakdown-list">
                  {conditionRows.map(([label, probability]) => (
                    <div
                      className="vision-breakdown-row"
                      key={label}
                    >
                      <div>
                        <span>{label}</span>
                        <strong>
                          {(probability * 100).toFixed(1)}%
                        </strong>
                      </div>

                      <div className="vision-mini-track">
                        <span
                          style={{
                            width: `${Math.min(
                              100,
                              probability * 100,
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </article>

              <article className="vision-stage-card">
                <div className="vision-stage-top">
                  <span>C</span>
                  <small>YOLO11s-Seg</small>
                </div>

                <h3>Visible defect segmentation</h3>

                <div className="vision-total-defect">
                  <span>Visible defect surface</span>
                  <strong>
                    {totalVisibleDefect.toFixed(2)}%
                  </strong>
                </div>

                <div className="vision-breakdown-list">
                  {visionDefectRows.map(([label, value]) => (
                    <div
                      className="vision-breakdown-row"
                      key={label}
                    >
                      <div>
                        <span>{label}</span>
                        <strong>
                          {value.toFixed(2)}%
                        </strong>
                      </div>

                      <div className="vision-mini-track">
                        <span
                          style={{
                            width: `${Math.min(
                              100,
                              value * 5,
                            )}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <small className="vision-surface-note">
                  Visible surface evidence only. Internal defects
                  are not inferred.
                </small>
              </article>

            </div>

            <div className="vision-trace-strip">
              <span>
                <strong>
                  {summary.images_analyzed ?? batch.images.length}
                </strong>
                uploaded images
              </span>

              <span>
                <strong>{independentImages}</strong>
                independent views
              </span>

              <span>
                <strong>{duplicatesIgnored}</strong>
                duplicates ignored
              </span>

              <span>
                <strong>
                  {assessment.confidence.toFixed(1)}%
                </strong>
                fusion confidence
              </span>
            </div>
          </>
        ) : (
          <div className="vision-fallback-state">
            <ShieldCheck size={24} />

            <div>
              <strong>
                Deterministic CV fallback used
              </strong>

              <p>
                Validated Model A, B and C weights were not active
                for this analysis. Once installed, this section will
                automatically display the learned evidence.
              </p>
            </div>
          </div>
        )}
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
            <article key={alt.action} className={index === 0 && alt.eligible !== false ? 'best-alternative' : ''}>
              <div className="alternative-top"><span>{index + 1}</span><StatusBadge value={actionLabel(alt.action, language)} /></div>
              <h3>{alt.title}</h3>
              <p>{alt.market}</p>
              <div className="alternative-profit">{alt.eligible === false ? alt.assumption_status || 'Pricing inputs needed' : formatCurrency(alt.net_profit, 0, language)}</div>
              {alt.price_source && <p>{alt.price_source}</p>}
              <div className="alternative-stats"><span><TrendingUp size={15} /> {t('result.roi')} {alt.roi.toFixed(1)}%</span><span><ShieldCheck size={15} /> {t('result.risk')} {alt.risk_score.toFixed(0)}</span></div>
            </article>
          ))}
        </div>
      </section>

      <footer className="result-footer">{t('result.analysisGenerated')} {formatDate(marketSnapshot?.analyzed_at || batch.updated_at, language)} · {assessment.feature_summary.images_analyzed || batch.images.length} {t('result.images')} · {assessment.feature_summary.potatoes_detected || '—'} {t('result.potatoRegions')}</footer>
    </>
  )
}
