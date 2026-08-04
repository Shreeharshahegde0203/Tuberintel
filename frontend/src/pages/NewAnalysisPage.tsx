import { Camera, CheckCircle2, ImagePlus, Info, Loader2, ScanLine, UploadCloud, X } from 'lucide-react'
import { useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/Common'
import { useI18n } from '../i18n/I18nContext'
import { analyzeBatch, createBatch, uploadBatchImages } from '../services/api'

const today = new Date().toISOString().slice(0, 10)

export default function NewAnalysisPage() {
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)
  const [files, setFiles] = useState<File[]>([])
  const [busy, setBusy] = useState(false)
  const [stage, setStage] = useState('Ready')
  const [error, setError] = useState('')
  const { language, t } = useI18n()
  const [form, setForm] = useState({
    variety: 'Kufri Jyoti', quantity_kg: 1000, farmer_name: '', source_location: 'Bengaluru Rural, Karnataka', state: 'Karnataka', district: 'Bengaluru Rural', harvest_date: today, intended_market: 'Kolar APMC', storage_cost_per_quintal_day: 8, storage_days: 14, transport_cost_per_km_tonne: 42, distance_km: 65, processor_price_per_quintal: '', handling_cost_per_quintal: 35, target_margin_percent: 10,
  })

  const previews = useMemo(() => files.map((file) => ({ file, url: URL.createObjectURL(file) })), [files])
  const update = (name: string, value: string | number) => setForm((current) => ({ ...current, [name]: value }))
  const appendFiles = (incoming: File[]) => { const valid = incoming.filter((file) => file.type.startsWith('image/')).slice(0, 12 - files.length); setFiles((current) => [...current, ...valid]) }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError('')
    if (files.length === 0) { setError(t('analysis.needImage')); return }
    setBusy(true)
    try {
      setStage(t('analysis.registering'))
      const batch = await createBatch({ variety: form.variety, quantity_kg: Number(form.quantity_kg), farmer_name: form.farmer_name || undefined, source_location: form.source_location, state: form.state, district: form.district || undefined, harvest_date: form.harvest_date || undefined, intended_market: form.intended_market || undefined })
      setStage(t('analysis.uploading')); await uploadBatchImages(batch.id, files)
      setStage(t('analysis.assessing'))
      await analyzeBatch(batch.id, { storage_cost_per_quintal_day: Number(form.storage_cost_per_quintal_day), storage_days: Number(form.storage_days), transport_cost_per_km_tonne: Number(form.transport_cost_per_km_tonne), distance_km: Number(form.distance_km), processor_price_per_quintal: form.processor_price_per_quintal === '' ? null : Number(form.processor_price_per_quintal), handling_cost_per_quintal: Number(form.handling_cost_per_quintal), target_margin_percent: Number(form.target_margin_percent), language })
      setStage(t('analysis.complete')); navigate(`/batches/${batch.id}`)
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      setError(typeof detail === 'string' ? detail : detail?.message || err.message || t('analysis.failed'))
    } finally { setBusy(false) }
  }

  const checks = ['analysis.check1', 'analysis.check2', 'analysis.check3', 'analysis.check4', 'analysis.check5', 'analysis.check6']
  return <>
    <PageHeader eyebrow={t('analysis.eyebrow')} title={t('analysis.title')} description={t('analysis.description')} />
    <form onSubmit={submit} className="analysis-layout">
      <div className="analysis-main">
        <section className="panel form-section">
          <div className="section-heading"><span className="step-number">01</span><div><h2>{t('analysis.identity')}</h2><p>{t('analysis.identityText')}</p></div></div>
          <div className="form-grid two-col">
            <label><span>{t('analysis.variety')}</span><input value={form.variety} onChange={(e) => update('variety', e.target.value)} required /></label>
            <label><span>{t('analysis.quantity')}</span><input type="number" min="1" value={form.quantity_kg} onChange={(e) => update('quantity_kg', Number(e.target.value))} required /></label>
            <label><span>{t('analysis.farmer')}</span><input value={form.farmer_name} onChange={(e) => update('farmer_name', e.target.value)} placeholder={t('analysis.optional')} /></label>
            <label><span>{t('analysis.harvest')}</span><input type="date" value={form.harvest_date} onChange={(e) => update('harvest_date', e.target.value)} /></label>
            <label className="span-2"><span>{t('analysis.source')}</span><input value={form.source_location} onChange={(e) => update('source_location', e.target.value)} required /></label>
            <label><span>{t('analysis.state')}</span><input value={form.state} onChange={(e) => update('state', e.target.value)} required /></label>
            <label><span>{t('analysis.district')}</span><input value={form.district} onChange={(e) => update('district', e.target.value)} /></label>
            <label className="span-2"><span>{t('analysis.preferredMarket')}</span><input value={form.intended_market} onChange={(e) => update('intended_market', e.target.value)} /></label>
          </div>
        </section>

        <section className="panel form-section">
          <div className="section-heading"><span className="step-number">02</span><div><h2>{t('analysis.imagery')}</h2><p>{t('analysis.imageryText')}</p></div></div>
          <div className="dropzone" onClick={() => fileInput.current?.click()} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); appendFiles(Array.from(e.dataTransfer.files)) }}>
            <input ref={fileInput} type="file" accept="image/jpeg,image/png,image/webp" multiple hidden onChange={(e) => appendFiles(Array.from(e.target.files || []))} />
            <div className="dropzone-icon"><UploadCloud size={30} /></div><strong>{t('analysis.drop')}</strong><span>{t('analysis.browse')}</span>
          </div>
          {previews.length > 0 && <div className="image-preview-grid">{previews.map(({ file, url }, index) => <div className="image-preview" key={`${file.name}-${index}`}><img src={url} alt={file.name} /><button type="button" onClick={() => setFiles((current) => current.filter((_, i) => i !== index))} aria-label={t('analysis.removeImage')}><X size={17} /></button><span>{file.name}</span></div>)}{files.length < 12 && <button type="button" className="add-image-tile" onClick={() => fileInput.current?.click()}><ImagePlus size={25} /><span>{t('analysis.addImage')}</span></button>}</div>}
          <div className="capture-guidance"><div><Camera size={22} /><span><strong>{t('analysis.cameraPosition')}</strong> {t('analysis.cameraPositionText')}</span></div><div><CheckCircle2 size={22} /><span><strong>{t('analysis.lighting')}</strong> {t('analysis.lightingText')}</span></div><div><ScanLine size={22} /><span><strong>{t('analysis.coverage')}</strong> {t('analysis.coverageText')}</span></div></div>
        </section>

        <section className="panel form-section">
          <div className="section-heading"><span className="step-number">03</span><div><h2>{t('analysis.economics')}</h2><p>{t('analysis.economicsText')}</p></div></div>
          <div className="form-grid three-col">
            <label><span>{t('analysis.distance')}</span><input type="number" min="0" value={form.distance_km} onChange={(e) => update('distance_km', Number(e.target.value))} /></label>
            <label><span>{t('analysis.transport')}</span><input type="number" min="0" value={form.transport_cost_per_km_tonne} onChange={(e) => update('transport_cost_per_km_tonne', Number(e.target.value))} /></label>
            <label><span>{t('analysis.handling')}</span><input type="number" min="0" value={form.handling_cost_per_quintal} onChange={(e) => update('handling_cost_per_quintal', Number(e.target.value))} /></label>
            <label><span>{t('analysis.storageDays')}</span><input type="number" min="0" max="180" value={form.storage_days} onChange={(e) => update('storage_days', Number(e.target.value))} /></label>
            <label><span>{t('analysis.storageCost')}</span><input type="number" min="0" value={form.storage_cost_per_quintal_day} onChange={(e) => update('storage_cost_per_quintal_day', Number(e.target.value))} /></label>
            <label><span>{t('analysis.processorQuote')}</span><input type="number" min="0" value={form.processor_price_per_quintal} onChange={(e) => update('processor_price_per_quintal', e.target.value)} placeholder={t('analysis.estimatedQuote')} /></label>
          </div>
        </section>
      </div>
      <aside className="analysis-sidebar"><div className="panel sticky-panel"><span className="panel-kicker">{t('analysis.scope')}</span><h2>{t('analysis.evaluates')}</h2><ul className="check-list">{checks.map((key) => <li key={key}><CheckCircle2 size={19} /> {t(key)}</li>)}</ul><div className="method-note"><Info size={21} /><p>{t('analysis.methodNote')}</p></div>{error && <div className="inline-error">{error}</div>}<button className="button button-primary button-full" disabled={busy} type="submit">{busy ? <><Loader2 className="spin" size={20} /> {stage}</> : <><ScanLine size={20} /> {t('analysis.run')}</>}</button><small className="fine-print">{t('analysis.disclaimer')}</small></div></aside>
    </form>
  </>
}
