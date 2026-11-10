import { BookOpen, MessageCircleQuestion, Send, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { readMarketLocation } from '../data/marketLocations'
import { useI18n } from '../i18n/I18nContext'
import { askFarmerAssistant } from '../services/api'

type ChatMessage = { role: 'assistant' | 'user'; text: string; sources?: string[] }

export function FarmerAssistant() {
  const { language } = useI18n()
  const route = useLocation()
  const marketLocation = readMarketLocation()
  const batchId = useMemo(() => {
    const match = route.pathname.match(/^\/batches\/(\d+)/)
    return match ? Number(match[1]) : undefined
  }, [route.pathname])
  const [open, setOpen] = useState(false)
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [suggestions, setSuggestions] = useState(language === 'kn'
    ? ['ಈ ಬ್ಯಾಚ್ ಈಗ ಮಾರಬೇಕಾ?', 'ಯಾವ ಮಂಡಿಯಲ್ಲಿ ಉತ್ತಮ ಬೆಲೆ ಇದೆ?', 'ಗ್ರೇಡ್ B ಫಲಿತಾಂಶ ವಿವರಿಸಿ']
    : ['Should I sell my latest batch?', 'Which mandi has the best price?', 'Explain my Grade B result'])
  const [messages, setMessages] = useState<ChatMessage[]>([{ role: 'assistant', text: language === 'kn' ? 'Tuber Mitra ನಿಮ್ಮ TuberIntel ಡೇಟಾ ಮತ್ತು ಆಲೂಗಡ್ಡೆ ಜ್ಞಾನ ಆಧರಿಸಿ ಉತ್ತರಿಸುತ್ತದೆ. ಗುಣಮಟ್ಟ, ಮಾರುಕಟ್ಟೆ, ಸಂಗ್ರಹಣೆ ಅಥವಾ ಮಾರಾಟದ ಬಗ್ಗೆ ಕೇಳಿ.' : 'Tuber Mitra answers using TuberIntel data and potato guidance. Ask about quality, market choices, storage, or selling decisions.' }])

  const ask = async (text: string) => {
    const value = text.trim()
    if (!value || busy) return
    setMessages((items) => [...items, { role: 'user', text: value }])
    setInput('')
    setBusy(true)
    try {
      const reply = await askFarmerAssistant({
        message: value,
        language,
        batch_id: batchId,
        state: marketLocation.state,
        district: marketLocation.district || undefined,
      })
      setMessages((items) => [...items, { role: 'assistant', text: reply.answer, sources: reply.sources.map((source) => source.title) }])
      setSuggestions(reply.suggestions)
    } catch (err: any) {
      setMessages((items) => [...items, { role: 'assistant', text: err?.response?.data?.detail || 'I could not reach the assistant service. The rest of TuberIntel is still available.' }])
    } finally {
      setBusy(false)
    }
  }

  return <>
    <button className="assistant-launcher" type="button" onClick={() => setOpen(true)} aria-label="Open Tuber Mitra">
      <MessageCircleQuestion size={19} />
      <span>Ask Tuber Mitra</span>
    </button>
    {open && <>
      <button className="assistant-backdrop" type="button" aria-label="Close Tuber Mitra" onClick={() => setOpen(false)} />
      <section className="assistant-panel" aria-label="Tuber Mitra farmer assistant" role="dialog" aria-modal="true">
        <header>
          <div className="assistant-avatar"><MessageCircleQuestion size={20} /></div>
          <div><strong>Tuber Mitra</strong><span>{language === 'kn' ? 'TuberIntel ಡೇಟಾ ಆಧಾರಿತ ಆಲೂಗಡ್ಡೆ ಮಾರ್ಗದರ್ಶನ' : 'Potato guidance using TuberIntel data'} · {batchId ? `Batch #${batchId}` : marketLocation.state}</span></div>
          <button onClick={() => setOpen(false)} aria-label="Close assistant"><X size={19} /></button>
        </header>
        <div className="assistant-context-bar"><BookOpen size={15} /><span>{language === 'kn' ? 'ಉತ್ತರಗಳು ಲಭ್ಯವಿರುವ ಬ್ಯಾಚ್, ಮಾರುಕಟ್ಟೆ ಮತ್ತು ಜ್ಞಾನ ಮೂಲಗಳಿಗೆ ಸೀಮಿತ.' : 'Answers are limited to available batch, market and knowledge context.'}</span></div>
        <div className="assistant-messages">
          {messages.map((message, index) => <article className={message.role} key={`${message.role}-${index}`}>
            <p>{message.text}</p>
            {message.sources && message.sources.length > 0 && <small><strong>Evidence:</strong> {message.sources.slice(0, 3).join(' · ')}</small>}
          </article>)}
          {busy && <article className="assistant"><p>Checking TuberIntel context…</p></article>}
        </div>
        <div className="assistant-suggestions">{suggestions.slice(0, 4).map((item) => <button type="button" key={item} onClick={() => void ask(item)}>{item}</button>)}</div>
        <form onSubmit={(e) => { e.preventDefault(); void ask(input) }}>
          <input value={input} onChange={(e) => setInput(e.target.value)} placeholder={language === 'kn' ? 'ನಿಮ್ಮ ಪ್ರಶ್ನೆ ಬರೆಯಿರಿ…' : 'Ask a potato question…'} />
          <button disabled={busy || !input.trim()} aria-label="Send"><Send size={18} /></button>
        </form>
        <footer>{language === 'kn' ? 'ಲೈವ್ ಬೆಲೆ, ಅಧಿಕೃತ ಗ್ರೇಡ್ ಅಥವಾ ಖರೀದಿದಾರರ ಒಪ್ಪಿಗೆ ಸಾಕ್ಷ್ಯವಿಲ್ಲದೆ ಸೃಷ್ಟಿಸಲಾಗುವುದಿಲ್ಲ.' : 'Live prices, official grades and buyer acceptance are never invented when evidence is unavailable.'}</footer>
      </section>
    </>}
  </>
}
