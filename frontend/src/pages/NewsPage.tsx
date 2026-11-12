import { ArrowUpRight, RefreshCw, Search, ThermometerSun } from 'lucide-react'
import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { LoadingState } from '../components/Common'
import { useI18n } from '../i18n/I18nContext'
import { getNews, getWeather } from '../services/api'
import { formatDate } from '../services/format'
import type { NewsResponse, WeatherResponse } from '../types'

export default function NewsPage() {
  const [params, setParams] = useSearchParams()
  const query = params.get('search') || ''
  const category = params.get('category') || ''
  const [search, setSearch] = useState(query)
  const [data, setData] = useState<NewsResponse | null>(null)
  const [weather, setWeather] = useState<WeatherResponse | null>(null)
  const [error, setError] = useState(false)
  const [loading, setLoading] = useState(true)
  const request = useRef<AbortController | null>(null)
  const { language, t } = useI18n()

  const load = useCallback(async (refresh = false) => {
    request.current?.abort()
    const controller = new AbortController()
    request.current = controller
    setLoading(true)
    setError(false)
    try {
      const news = await getNews({ category, search: query, limit: 40, refresh }, controller.signal)
      if (!controller.signal.aborted) setData(news)
    } catch {
      if (!controller.signal.aborted) setError(true)
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }, [category, query])

  useEffect(() => {
    void load()
    return () => request.current?.abort()
  }, [load])

  useEffect(() => { setSearch(query) }, [query])
  useEffect(() => {
    getWeather(12.9716, 77.5946, 5).then(setWeather).catch(() => undefined)
  }, [])

  const updateFilter = (key: 'search' | 'category', value: string) => {
    const next = new URLSearchParams(params)
    if (value) next.set(key, value)
    else next.delete(key)
    setParams(next)
  }

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    updateFilter('search', search.trim())
  }

  const number = (value: number | null, unit: string) => value === null ? '—' : `${Math.round(value)}${unit}`

  return <>
    <section className="page-intro">
      <div><span className="section-kicker">{t('news.eyebrow')}</span><h1>{t('news.title')}</h1><p>{t('news.description')}</p></div>
      <div className="page-intro-actions">
        <button className="button button-secondary" type="button" onClick={() => void load(true)} disabled={loading}>
          <RefreshCw size={18} />{t('news.refresh')}
        </button>
      </div>
    </section>

    <section className="news-toolbar">
      <form onSubmit={submitSearch}>
        <Search size={19} aria-hidden="true" />
        <input aria-label={t('news.searchPlaceholder')} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t('news.searchPlaceholder')} />
        <button type="submit">{t('common.search')}</button>
      </form>
      <div className="news-categories" aria-label="News categories">
        {['', ...new Set([...(data?.categories || []), ...(category ? [category] : [])])].map((item) =>
          <button key={item} type="button" aria-pressed={category === item} className={category === item ? 'active' : ''} onClick={() => updateFilter('category', item)}>
            {item || t('common.all')}
          </button>,
        )}
      </div>
    </section>

    <section className="news-layout">
      <div className="news-main-column" aria-busy={loading}>
        {loading ? <LoadingState /> : error ? <div className="compact-empty" role="alert">{t('news.unavailable')} <button className="button button-secondary" onClick={() => void load()}>{t('news.retry')}</button></div>
          : data?.articles.length ? data.articles.map((article) =>
            <a className="news-card" key={article.id} href={article.url} target="_blank" rel="noreferrer">
              <div className="news-card-copy">
                <span>{article.category}</span>
                <h2 className="news-link-title">{article.title}</h2>
                {article.summary && <p>{article.summary}</p>}
                <div><small>{[article.source, article.published_at && formatDate(article.published_at, language)].filter(Boolean).join(' · ')}</small><ArrowUpRight size={16} aria-hidden="true" /></div>
              </div>
            </a>,
          ) : <div className="compact-empty">{t('news.empty')}</div>}
      </div>

      <aside className="news-side-column">
        <article className="weather-card">
          <div className="weather-card-head"><div><span className="section-kicker">{t('weather.update')}</span><h2>{t('weather.bengaluru')}</h2></div><ThermometerSun size={25}/></div>
          {weather ? <>
            <div className="weather-current"><strong>{number(weather.current_temperature, '°C')}</strong><span>{t('weather.current')}</span></div>
            <div className="weather-facts">
              <div><span>{t('weather.humidity')}</span><strong>{number(weather.current_humidity, '%')}</strong></div>
              <div><span>{t('weather.wind')}</span><strong>{number(weather.current_wind_speed, ' km/h')}</strong></div>
            </div>
            <div className="weather-days">{weather.daily.map((day) => <div key={day.date}><span>{new Date(day.date).toLocaleDateString(language === 'kn' ? 'kn-IN' : 'en-IN', { weekday: 'short', timeZone: 'Asia/Kolkata' })}</span><strong>{Math.round(day.maximum_temperature)}°</strong><small>{Math.round(day.precipitation_probability)}% {t('weather.rain')}</small></div>)}</div>
            <small className="weather-source">{weather.source}</small>
          </> : <div className="compact-empty">{t('weather.unavailable')}</div>}
        </article>
        {data && !loading && !error && <article className="market-panel news-source-card" aria-live="polite">
          <span className="section-kicker">{t('news.sources')}</span><h2>{t('news.sourceTitle')}</h2>
          <p>{data.note}</p>
          {data.freshness !== 'unavailable' && <p>{t('news.lastUpdate')} · {new Date(data.freshness).toLocaleString(language === 'kn' ? 'kn-IN' : 'en-IN', { timeZone: 'Asia/Kolkata', dateStyle: 'medium', timeStyle: 'short' })} IST</p>}
          <div>{data.sources.slice(0, 8).map((source) => <span key={source}>{source}</span>)}</div>
        </article>}
      </aside>
    </section>
  </>
}
