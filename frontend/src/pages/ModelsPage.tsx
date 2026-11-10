import { CheckCircle2, Cpu, Database, Eye, GitBranch, Layers3, ShieldCheck, TriangleAlert } from 'lucide-react'
import { useEffect, useState } from 'react'
import { ErrorState, LoadingState, PageHeader, StatusBadge } from '../components/Common'
import { useI18n } from '../i18n/I18nContext'
import { getModelStatus } from '../services/api'
import type { ModelStatusResponse } from '../types'

export default function ModelsPage() {
  const [data, setData] = useState<ModelStatusResponse | null>(null)
  const [error, setError] = useState('')
  const { language, t } = useI18n()
  const load = () => getModelStatus().then(setData).catch((err) => setError(err?.response?.data?.detail || err.message))
  useEffect(() => { void load() }, [])
  if (error) return <ErrorState message={String(error)} retry={load} />
  if (!data) return <LoadingState />

  const pipeline = [
    {
      icon: Eye,
      title: 'Image acquisition',
      text: 'Smartphone or RGB images with lighting and capture-quality checks.',
    },
    {
      icon: Layers3,
      title: 'Model A ? ROI',
      text: 'YOLO11n-Seg produces per-potato masks, regions and shape evidence.',
    },
    {
      icon: Cpu,
      title: 'Model B ? Condition',
      text: 'YOLO11s-Cls classifies each ROI as Healthy, Damaged, Defected, Diseased-Fungal or Sprouted.',
    },
    {
      icon: Layers3,
      title: 'Model C ? Defects',
      text: 'YOLO11s-Seg segments visible Scab, Rot, Greening and Mechanical Damage regions.',
    },
    {
      icon: GitBranch,
      title: 'Fusion + decision',
      text: 'Vision evidence, deterministic CV safeguards, mandi price and the 30-day forecast feed Sell / Store / Process / Wait ranking.',
    },
  ]

  return <>
    <PageHeader eyebrow={t('models.eyebrow')} title={t('models.title')} description={t('models.description')} />
    <div className="research-warning"><TriangleAlert size={22} /><div><strong>{t('models.research')}</strong><p>{t('models.researchText')}</p></div></div>
    <section className="pipeline-strip">{pipeline.map(({ icon: Icon, title, text }, index) => <article key={title}><span className="pipeline-number">0{index + 1}</span><Icon size={23} /><h3>{title}</h3><p>{text}</p></article>)}</section>
    <section className="model-grid">
      {data.models.map((model) => <article className="panel model-card" key={model.name}><div className="model-card-top"><div className="model-icon"><Layers3 size={24} /></div><StatusBadge value={model.loaded ? t('models.loaded') : model.configured ? t('models.configured') : t('models.notConfigured')} /></div><h2>{model.name}</h2><p className="model-role">{model.role}</p><div className="model-path"><span>{language === 'kn' ? 'ತೂಕಗಳ ಮಾರ್ಗ' : 'Weight path'}</span><code>{model.path || (language === 'kn' ? 'ಹೊಂದಿಸಿಲ್ಲ' : 'Not set')}</code></div><p>{model.note}</p>{model.loaded ? <div className="model-status-good"><CheckCircle2 size={18} /> {language === 'kn' ? 'ಇನ್‌ಫರೆನ್ಸ್‌ಗೆ ಸಿದ್ಧ' : 'Ready for inference'}</div> : <div className="model-status-warning"><TriangleAlert size={18} /> {language === 'kn' ? 'ತರಬೇತಿ ಆರ್ಟಿಫ್ಯಾಕ್ಟ್ ಅಗತ್ಯ' : 'Training artefact required'}</div>}</article>)}
      <article className="panel model-card fallback-card"><div className="model-card-top"><div className="model-icon"><Cpu size={24} /></div><StatusBadge value={language === 'kn' ? 'ಸಕ್ರಿಯ' : 'Active'} /></div><h2>{data.fallback.name}</h2><p className="model-role">{language === 'kn' ? 'ನಿರ್ಧಾರಾತ್ಮಕ, ವಿವರಣಾತ್ಮಕ ಮೂಲ ಮಾದರಿ ಮತ್ತು ಸುರಕ್ಷಿತ ಪರ್ಯಾಯ.' : 'Deterministic, explainable baseline and safe fallback.'}</p><ul className="feature-list">{data.fallback.features.map((feature) => <li key={feature}><CheckCircle2 size={18} /> {feature}</li>)}</ul></article>
    </section>
    <section className="panel methodology-panel">
      <div>
        <span className="panel-kicker">
          TuberIntel Vision v1
        </span>

        <h2>
          YOLO11n-Seg ? YOLO11s-Cls ? YOLO11s-Seg ? Fusion
        </h2>

        <p>
          Only validated best weights are activated for production
          inference. Model A supplies potato ROIs, Model B supplies
          condition evidence, and Model C supplies visible-surface
          defect masks. The result is advisory and is not an AGMARK
          certification.
        </p>
      </div>

      <div className="methodology-columns">
        <div>
          <strong>Validation rules</strong>
          <span>Leakage-safe train / validation / test separation</span>
          <span>Untouched test only after final model selection</span>
          <span>External-domain testing and confidence abstention</span>
          <span>Version traceability for every model artifact</span>
        </div>

        <div>
          <strong>Primary metrics</strong>
          <span>Model A ? Mask mAP50-95 / IoU</span>
          <span>Model B ? Macro F1 / balanced accuracy</span>
          <span>Model C ? Per-class mask mAP50-95</span>
          <span>OpenVINO CPU latency / confidence calibration</span>
        </div>
      </div>
    </section>
  </>
}
