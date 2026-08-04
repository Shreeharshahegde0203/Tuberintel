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

  const pipeline = language === 'kn' ? [
    { icon: Eye, title: 'ಚಿತ್ರ ಸೆರೆಹಿಡಿಯುವುದು', text: 'ಸ್ಮಾರ್ಟ್‌ಫೋನ್ ಅಥವಾ RGB ಕ್ಯಾಮೆರಾ ಚಿತ್ರಗಳು ಮತ್ತು ಗುಣಮಟ್ಟ ಪರಿಶೀಲನೆ.' },
    { icon: Cpu, title: 'ದೃಶ್ಯ ಮೌಲ್ಯಮಾಪನ', text: 'ಸೆಗ್ಮೆಂಟೇಶನ್, ಜ್ಯಾಮಿತಿ, ಬಣ್ಣ, ವಿನ್ಯಾಸ ಮತ್ತು ತರಬೇತುಗೊಂಡ ದೋಷ ಮಾದರಿಗಳು.' },
    { icon: Database, title: 'ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ', text: 'ಮಂಡಿ ಬೆಲೆ, ಇತಿಹಾಸ, ಸಂಗ್ರಹಣೆ, ಸಾಗಣೆ ಮತ್ತು ಬೇಡಿಕೆ.' },
    { icon: GitBranch, title: 'ನಿರ್ಧಾರ ಎಂಜಿನ್', text: 'ಮಾರಾಟ, ಸಂಗ್ರಹಣೆ, ಸಂಸ್ಕರಣೆ ಮತ್ತು ಕಾಯುವ ಮಾರ್ಗಗಳ ಪಾರದರ್ಶಕ ಶ್ರೇಯಾಂಕ.' },
    { icon: ShieldCheck, title: 'ವಿವರಣಾತ್ಮಕ ಫಲಿತಾಂಶ', text: 'ಲಕ್ಷಣ ಕೊಡುಗೆ, ದೃಶ್ಯ ಓವರ್‌ಲೇ, ವೆಚ್ಚ ಮತ್ತು ಅಪಾಯದ ಕಾರಣ.' },
  ] : [
    { icon: Eye, title: 'Image acquisition', text: 'Smartphone or RGB camera images with quality checks.' },
    { icon: Cpu, title: 'Visual assessment', text: 'Segmentation, geometry, colour, texture and trained defect models.' },
    { icon: Database, title: 'Market intelligence', text: 'Mandi price, history, storage, transport and demand inputs.' },
    { icon: GitBranch, title: 'Decision engine', text: 'Transparent ranking of sell, store, process and wait pathways.' },
    { icon: ShieldCheck, title: 'Explainability', text: 'Feature contribution, visual overlays, costs and risk reasoning.' },
  ]

  return <>
    <PageHeader eyebrow={t('models.eyebrow')} title={t('models.title')} description={t('models.description')} />
    <div className="research-warning"><TriangleAlert size={22} /><div><strong>{t('models.research')}</strong><p>{t('models.researchText')}</p></div></div>
    <section className="pipeline-strip">{pipeline.map(({ icon: Icon, title, text }, index) => <article key={title}><span className="pipeline-number">0{index + 1}</span><Icon size={23} /><h3>{title}</h3><p>{text}</p></article>)}</section>
    <section className="model-grid">
      {data.models.map((model) => <article className="panel model-card" key={model.name}><div className="model-card-top"><div className="model-icon"><Layers3 size={24} /></div><StatusBadge value={model.loaded ? t('models.loaded') : model.configured ? t('models.configured') : t('models.notConfigured')} /></div><h2>{model.name}</h2><p className="model-role">{model.role}</p><div className="model-path"><span>{language === 'kn' ? 'ತೂಕಗಳ ಮಾರ್ಗ' : 'Weight path'}</span><code>{model.path || (language === 'kn' ? 'ಹೊಂದಿಸಿಲ್ಲ' : 'Not set')}</code></div><p>{model.note}</p>{model.loaded ? <div className="model-status-good"><CheckCircle2 size={18} /> {language === 'kn' ? 'ಇನ್‌ಫರೆನ್ಸ್‌ಗೆ ಸಿದ್ಧ' : 'Ready for inference'}</div> : <div className="model-status-warning"><TriangleAlert size={18} /> {language === 'kn' ? 'ತರಬೇತಿ ಆರ್ಟಿಫ್ಯಾಕ್ಟ್ ಅಗತ್ಯ' : 'Training artefact required'}</div>}</article>)}
      <article className="panel model-card fallback-card"><div className="model-card-top"><div className="model-icon"><Cpu size={24} /></div><StatusBadge value={language === 'kn' ? 'ಸಕ್ರಿಯ' : 'Active'} /></div><h2>{data.fallback.name}</h2><p className="model-role">{language === 'kn' ? 'ನಿರ್ಧಾರಾತ್ಮಕ, ವಿವರಣಾತ್ಮಕ ಮೂಲ ಮಾದರಿ ಮತ್ತು ಸುರಕ್ಷಿತ ಪರ್ಯಾಯ.' : 'Deterministic, explainable baseline and safe fallback.'}</p><ul className="feature-list">{data.fallback.features.map((feature) => <li key={feature}><CheckCircle2 size={18} /> {feature}</li>)}</ul></article>
    </section>
    <section className="panel methodology-panel"><div><span className="panel-kicker">{language === 'kn' ? 'ಅಂತಿಮ ಹೈಬ್ರಿಡ್ ಅಭ್ಯರ್ಥಿಗಳು' : 'Final hybrid candidates'}</span><h2>YOLO/Mask R-CNN + EfficientNetV2/ConvNeXt + calibrated geometry</h2><p>{language === 'kn' ? 'ಒಂದೇ ಮಾದರಿಯನ್ನು ಮೊದಲು ಉತ್ತಮ ಎಂದು ಘೋಷಿಸಲಾಗುವುದಿಲ್ಲ. ಒಂದೇ ಗುಂಪು-ಆಧಾರಿತ ಬಾಹ್ಯ ಪರೀಕ್ಷೆಯಲ್ಲಿ ಸೆಗ್ಮೆಂಟೇಶನ್, ವರ್ಗೀಕರಣ, ಕ್ಯಾಲಿಬ್ರೇಷನ್, ವೇಗ ಮತ್ತು ತೀವ್ರ ದೋಷ ರಿಕಾಲ್ ಆಧಾರವಾಗಿ ಆಯ್ಕೆ ಮಾಡಲಾಗುತ್ತದೆ.' : 'No model is declared best in advance. Segmentation and classifier families are compared on the same grouped external test set using macro F1, calibration, severe-defect recall, area error and latency.'}</p></div><div className="methodology-columns"><div><strong>{language === 'kn' ? 'ಡೇಟಾ ನಿಯಮಗಳು' : 'Data rules'}</strong><span>{language === 'kn' ? 'ಮೂಲ ಚಿತ್ರ ಮತ್ತು ಆಗ್ಮೆಂಟೇಶನ್ ಬೇರ್ಪಡಿಕೆ' : 'Original/augmentation parent-aware splits'}</span><span>{language === 'kn' ? 'ನಕಲು ಮತ್ತು ಮೂಲ ಪರಿಶೀಲನೆ' : 'Duplicate and provenance audit'}</span><span>{language === 'kn' ? 'ಕರ್ನಾಟಕದ ಬಾಹ್ಯ ಪರೀಕ್ಷಾ ಸೆಟ್' : 'Karnataka external test set'}</span></div><div><strong>{language === 'kn' ? 'ಪ್ರಾಥಮಿಕ ಮಾನದಂಡಗಳು' : 'Primary metrics'}</strong><span>Macro F1 / balanced accuracy</span><span>mAP50-95 / Dice / IoU</span><span>Calibration / abstention risk</span><span>Weighted grading kappa</span></div></div></section>
  </>
}
