import { Camera, CheckCircle2, ImagePlus, Info, Loader2, ScanLine, UploadCloud, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageHeader } from '../components/Common'
import { readMarketLocation, type MarketLocation } from '../data/marketLocations'
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
  const [marketLocation, setMarketLocation] = useState<MarketLocation>(() => readMarketLocation())
  const [form, setForm] = useState({
    quality_pricing_mode: 'estimated', fresh_buyer_price_per_quintal: '', buyer_quality_discount_percent: '', saleable_weight_percent: '', 
    variety: '', quantity_kg: 1000, source_district: 'Bengaluru Rural', harvest_date: today, storage_cost_per_quintal_day: 8, storage_days: 14, transport_cost_per_km_tonne: 42, distance_km: 65, processor_price_per_quintal: '', handling_cost_per_quintal: 35, target_margin_percent: 10, measurement_source: 'not_available', measured_length_mm: '', measured_width_mm: '',
  })

  useEffect(() => {
    const listener = (event: Event) => setMarketLocation((event as CustomEvent<MarketLocation>).detail)
    window.addEventListener('tuberintel-location', listener)
    return () => window.removeEventListener('tuberintel-location', listener)
  }, [])

  const previews = useMemo(() => files.map((file) => ({ file, url: URL.createObjectURL(file) })), [files])
  const update = (name: string, value: string | number) => setForm((current) => ({ ...current, [name]: value }))
  const appendFiles = (incoming: File[]) => { const valid = incoming.filter((file) => file.type.startsWith('image/')).slice(0, 12 - files.length); setFiles((current) => [...current, ...valid]) }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault(); setError('')
    if (files.length === 0) { setError(t('analysis.needImage')); return }
    setBusy(true)
    try {
      const sourceDistrict = String(form.source_district || marketLocation.district).trim()
      setStage(t('analysis.registering'))
      const batch = await createBatch({
        variety: String(form.variety).trim() || 'Unspecified',
        quantity_kg: Number(form.quantity_kg),
        source_location: `${sourceDistrict}, ${marketLocation.state}`,
        state: marketLocation.state,
        district: sourceDistrict || undefined,
        harvest_date: form.harvest_date || undefined,
        intended_market: marketLocation.market || undefined,
      })
      setStage(t('analysis.uploading')); await uploadBatchImages(batch.id, files)
      setStage(t('analysis.assessing'))
      await analyzeBatch(batch.id, { quality_pricing_mode: form.quality_pricing_mode as 'estimated' | 'manual' | 'reference', fresh_buyer_price_per_quintal: form.fresh_buyer_price_per_quintal === '' ? null : Number(form.fresh_buyer_price_per_quintal), buyer_quality_discount_percent: form.buyer_quality_discount_percent === '' ? null : Number(form.buyer_quality_discount_percent), saleable_weight_percent: form.saleable_weight_percent === '' ? null : Number(form.saleable_weight_percent),  storage_cost_per_quintal_day: Number(form.storage_cost_per_quintal_day), storage_days: Number(form.storage_days), transport_cost_per_km_tonne: Number(form.transport_cost_per_km_tonne), distance_km: Number(form.distance_km), processor_price_per_quintal: form.processor_price_per_quintal === '' ? null : Number(form.processor_price_per_quintal), handling_cost_per_quintal: Number(form.handling_cost_per_quintal), target_margin_percent: Number(form.target_margin_percent), language, measurement_source: form.measurement_source as 'not_available' | 'manual' | 'potato_ruler' | 'calibrated_image', measured_length_mm: form.measured_length_mm === '' ? null : Number(form.measured_length_mm), measured_width_mm: form.measured_width_mm === '' ? null : Number(form.measured_width_mm) })
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
            <label><span>{t('analysis.quantity')}</span><input type="number" min="1" value={form.quantity_kg} onChange={(e) => update('quantity_kg', Number(e.target.value))} required /></label>
            <label><span>{t('analysis.harvest')}</span><input type="date" value={form.harvest_date} onChange={(e) => update('harvest_date', e.target.value)} /></label>
            <label><span>Source district</span><input value={form.source_district} onChange={(e) => update('source_district', e.target.value)} placeholder={marketLocation.district || 'District'} /></label>
            <label><span>{t('analysis.variety')} ({t('analysis.optional')})</span><input value={form.variety} onChange={(e) => update('variety', e.target.value)} placeholder="Not specified" /></label>
            <div className="selected-market-inline span-2">
              <div><span>Selected market</span><strong>{marketLocation.market || 'No market selected'}</strong></div>
              <small>{[marketLocation.district, marketLocation.state].filter(Boolean).join(', ')} Â· Uses the market selector above.</small>
            </div>
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
          <div className="measurement-box">
            <div><strong>{language === 'kn' ? 'à²à²šà³à²›à²¿à²• à²­à³Œà²¤à²¿à²• à²—à²¾à²¤à³à²°' : 'Optional physical size'}</strong><p>{language === 'kn' ? 'à²«à³‹à²Ÿà³‹ à²ªà²¿à²•à³à²¸à³†à²²à³â€Œà²—à²³à²¨à³à²¨à³ mm à²Žà²‚à²¦à³ à²Šà²¹à²¿à²¸à³à²µà³à²¦à²¿à²²à³à²². à²°à³à²²à²°à³/Potato Ruler/à²•à³à²¯à²¾à²²à²¿à²¬à³à²°à³‡à²Ÿà³†à²¡à³ à²šà²¿à²¤à³à²° à²‡à²¦à³à²¦à²¾à²— à²®à²¾à²¤à³à²° mm à²¨à³€à²¡à²¿.' : 'TuberIntel never treats photo pixels as millimetres. Enter mm only when you used a ruler, Potato Ruler, or a calibrated image.'}</p></div>
            <div className="form-grid three-col">
              <label><span>{language === 'kn' ? 'à²®à²¾à²ªà²¨ à²®à³‚à²²' : 'Measurement source'}</span><select value={form.measurement_source} onChange={(e) => e.target.value === 'not_available' ? setForm((current) => ({ ...current, measurement_source: 'not_available', measured_length_mm: '', measured_width_mm: '' })) : update('measurement_source', e.target.value)}><option value="not_available">No calibrated measurement</option><option value="manual">Manual ruler / caliper</option><option value="potato_ruler">Potato Ruler</option><option value="calibrated_image">Calibrated image</option></select></label>
              <label><span>{language === 'kn' ? 'à²‰à²¦à³à²¦ (mm)' : 'Length (mm)'}</span><input type="number" min="1" step="0.1" disabled={form.measurement_source === 'not_available'} value={form.measured_length_mm} onChange={(e) => update('measured_length_mm', e.target.value)} placeholder="e.g. 72" /></label>
              <label><span>{language === 'kn' ? 'à²…à²—à²² (mm)' : 'Width (mm)'}</span><input type="number" min="1" step="0.1" disabled={form.measurement_source === 'not_available'} value={form.measured_width_mm} onChange={(e) => update('measured_width_mm', e.target.value)} placeholder="e.g. 54" /></label>
            </div>
          </div>
        </section>

        <section className="panel form-section assumptions-section">
          <details className="assumption-details">
            <summary>
              <span className="assumption-summary-main"><span className="step-number">03</span><span><strong>{t('analysis.economics')}</strong><small>Using recommended defaults. Open this only when you want to change transport, storage or processor assumptions.</small></span></span>
              <span className="assumption-edit">Edit assumptions</span>
            </summary>
            <div className="form-grid three-col assumption-fields">
              <label><span>{t('analysis.distance')}</span><input type="number" min="0" value={form.distance_km} onChange={(e) => update('distance_km', Number(e.target.value))} /></label>
              <label><span>{t('analysis.transport')}</span><input type="number" min="0" value={form.transport_cost_per_km_tonne} onChange={(e) => update('transport_cost_per_km_tonne', Number(e.target.value))} /></label>
              <label><span>{t('analysis.handling')}</span><input type="number" min="0" value={form.handling_cost_per_quintal} onChange={(e) => update('handling_cost_per_quintal', Number(e.target.value))} /></label>
              <label><span>{t('analysis.storageDays')}</span><input type="number" min="0" max="180" value={form.storage_days} onChange={(e) => update('storage_days', Number(e.target.value))} /></label>
              <label><span>{t('analysis.storageCost')}</span><input type="number" min="0" value={form.storage_cost_per_quintal_day} onChange={(e) => update('storage_cost_per_quintal_day', Number(e.target.value))} /></label>
              <label><span>{t('analysis.processorQuote')}</span><input type="number" min="0" value={form.processor_price_per_quintal} onChange={(e) => update('processor_price_per_quintal', e.target.value)} placeholder={t('analysis.estimatedQuote')} /></label>
            </div>
          </details>
        </section>

          {/* TUBERINTEL QUALITY VALUE V1 */}
          <div className="form-grid two-col">
            <label><span>{language === 'kn' ? 'ಮೌಲ್ಯ ಲೆಕ್ಕದ ವಿಧಾನ' : 'Quality valuation mode'}</span><select value={form.quality_pricing_mode} onChange={(e) => update('quality_pricing_mode', e.target.value)}><option value="estimated">Quality-adjusted estimate (prototype)</option><option value="manual">Buyer terms / manual pricing</option><option value="reference">Market reference only</option></select></label>
            <label><span>{language === 'kn' ? 'ತಾಜಾ ಮಾರುಕಟ್ಟೆ ಖರೀದಿದಾರರ ದರ (₹/ಕ್ವಿಂಟಲ್)' : 'Fresh buyer quote (₹/quintal, optional)'}</span><input type="number" min="0" step="any" value={form.fresh_buyer_price_per_quintal} onChange={(e) => update('fresh_buyer_price_per_quintal', e.target.value)} placeholder="Applies to sell now only" /></label>
            <label><span>{language === 'kn' ? 'ಖರೀದಿದಾರರ ಗುಣಮಟ್ಟ ಕಡಿತ (%)' : 'Buyer quality discount (%, optional)'}</span><input type="number" min="0" max="100" step="any" value={form.buyer_quality_discount_percent} onChange={(e) => update('buyer_quality_discount_percent', e.target.value)} placeholder="Overrides the prototype price curve" /></label>
            <label><span>{language === 'kn' ? 'ಮಾರಾಟಯೋಗ್ಯ ತೂಕ (%)' : 'Measured / assumed saleable weight (%, optional)'}</span><input type="number" min="0" max="100" step="any" value={form.saleable_weight_percent} onChange={(e) => update('saleable_weight_percent', e.target.value)} placeholder="Blank retains 100%; not inferred from pixels" /></label>
          </div>
          <p className="fine-print">{language === 'kn' ? 'ಚಿತ್ರದ ಗುಣಮಟ್ಟದಿಂದ ಅಂದಾಜು ಮೌಲ್ಯ ಬದಲಾಗುತ್ತದೆ. ಇದು ಸ್ಥಳೀಯ ಖರೀದಿದಾರರ ಬೆಲೆಗಳಿಗೆ ಇನ್ನೂ ದೃಢೀಕರಿಸದ ಮಾದರಿ ಲೆಕ್ಕ. ನಿಜವಾದ ದರ ಮತ್ತು ಮಾರಾಟಯೋಗ್ಯ ತೂಕ ನೀಡಿದರೆ ಅವಕ್ಕೆ ಆದ್ಯತೆ.' : 'The prototype estimate varies with fused quality scores. It is not calibrated to local buyer prices. Buyer discounts and measured saleable weight override assumptions; a fresh-buyer quote overrides the sell-now price. Re-use different, representative potatoes rather than repeated views.'}</p>
      </div>
      <aside className="analysis-sidebar"><div className="panel sticky-panel"><span className="panel-kicker">{t('analysis.scope')}</span><h2>{t('analysis.evaluates')}</h2><ul className="check-list">{checks.map((key) => <li key={key}><CheckCircle2 size={19} /> {t(key)}</li>)}</ul><div className="method-note"><Info size={21} /><p>{t('analysis.methodNote')}</p></div>{error && <div className="inline-error">{error}</div>}<button className="button button-primary button-full" disabled={busy} type="submit">{busy ? <><Loader2 className="spin" size={20} /> {stage}</> : <><ScanLine size={20} /> {t('analysis.run')}</>}</button><small className="fine-print">{t('analysis.disclaimer')}</small></div></aside>
    </form>
  </>
}

