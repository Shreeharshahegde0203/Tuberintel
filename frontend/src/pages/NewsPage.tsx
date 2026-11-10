import { ArrowUpRight, CloudRain, ExternalLink, Newspaper, RefreshCw, Search, ThermometerSun, Wind } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { ErrorState, LoadingState } from '../components/Common'
import { useI18n } from '../i18n/I18nContext'
import { getNews, getWeather, refreshNews } from '../services/api'
import { formatDate } from '../services/format'
import type { NewsResponse, WeatherResponse } from '../types'

const categoryColors: Record<string, string> = {
  Market: 'market', Weather: 'weather', Government: 'government', Storage: 'storage', Research: 'research', Disease: 'disease', Processing: 'processing',
}

export default function NewsPage() {
  const [params, setParams] = useSearchParams()
  const [data, setData] = useState<NewsResponse | null>(null)
  const [weather, setWeather] = useState<WeatherResponse | null>(null)
  const [category, setCategory] = useState('')
  const [search, setSearch] = useState(params.get('search') || '')
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const { language, t } = useI18n()

  const load = async (forceRefresh = false) => {
    setError('')
    try {
      const news = await getNews({ category: category || undefined, search: search || undefined, limit: 40, refresh: forceRefresh })
      setData(news)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message)
    }
  }

  useEffect(() => { load(false) }, [category])
  useEffect(() => {
    getWeather(12.9716, 77.5946, 5).then(setWeather).catch(() => undefined)
  }, [])

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault()
    setParams(search ? { search } : {})
    load(false)
  }

  const forceRefresh = async () => {
    setRefreshing(true)
    try { await refreshNews(); await load(false) } finally { setRefreshing(false) }
  }

  const featured = data?.articles[0]
  const remaining = useMemo(() => data?.articles.slice(1) || [], [data])

  if (error) return <ErrorState message={String(error)} retry={() => load(false)} />
  if (!data) return <LoadingState />

  return <>
    <section className="page-intro">
      <div><span className="section-kicker">{t('news.eyebrow')}</span><h1>{t('news.title')}</h1><p>{t('news.description')}</p></div>
      <div className="page-intro-actions"><button className="button button-secondary" type="button" onClick={forceRefresh} disabled={refreshing}><RefreshCw className={refreshing ? 'spin' : ''} size={18}/>{t('news.refresh')}</button></div>
    </section>

    <section className="news-toolbar">
      <form onSubmit={submitSearch}><Search size={19}/><input value={search} onChange={(e) => setSearch(e.target.value)} placeholder={t('news.searchPlaceholder')}/><button type="submit">{t('common.search')}</button></form>
      <div className="news-categories"><button className={!category ? 'active' : ''} onClick={() => setCategory('')}>{t('common.all')}</button>{data.categories.map((item) => <button className={category === item ? 'active' : ''} key={item} onClick={() => setCategory(item)}>{item}</button>)}</div>
    </section>

    <section className="news-layout">
      <div className="news-main-column">
        {featured ? <a className="featured-news-card" href={featured.url} target="_blank" rel="noreferrer">
          <div className={`featured-news-visual ${categoryColors[featured.category] || 'default'}`}><Newspaper size={54}/><span>{featured.category}</span></div>
          <div className="featured-news-copy"><span className="news-category-badge">{featured.category}</span><h2
            className="news-link-title"
            style={{
              color: '#0969da',
              textDecoration: 'underline',
              textDecorationThickness: '1.5px',
              textUnderlineOffset: '3px',
              cursor: 'pointer',
            }}
          >
            {featured.title}
          </h2><p>{featured.summary || t('news.openAtSource')}</p><div><span>{featured.source} · {featured.published_at ? formatDate(featured.published_at, language) : t('common.recent')}</span><strong>{t('news.readOriginal')}<ArrowUpRight size={17}/></strong></div></div>
        </a> : <div className="market-panel compact-empty">{t('news.empty')}</div>}

        <div className="news-card-grid">{remaining.map((article) => <a className="news-card" key={article.id} href={article.url} target="_blank" rel="noreferrer"><div className={`news-card-visual ${categoryColors[article.category] || 'default'}`}><Newspaper size={28}/><span>{article.category}</span></div><div className="news-card-copy"><span>{article.category}</span><h3
          className="news-link-title"
          style={{
            color: '#0969da',
            textDecoration: 'underline',
            textDecorationThickness: '1.5px',
            textUnderlineOffset: '3px',
            cursor: 'pointer',
          }}
        >
          {article.title}
        </h3><p>{article.summary || t('news.openAtSource')}</p><div><small>{article.source}</small><ExternalLink size={16}/></div></div></a>)}</div>
      </div>

      <aside className="news-side-column">
        <article className="weather-card">
          <div className="weather-card-head"><div><span className="section-kicker">{t('weather.update')}</span><h2>{t('weather.bengaluru')}</h2></div><ThermometerSun size={25}/></div>
          {weather ? <><div className="weather-current"><strong>{Math.round(weather.current_temperature || 0)}°C</strong><span>{t('weather.current')}</span></div><div className="weather-facts"><div><CloudRain size={18}/><span>{t('weather.humidity')}</span><strong>{Math.round(weather.current_humidity || 0)}%</strong></div><div><Wind size={18}/><span>{t('weather.wind')}</span><strong>{Math.round(weather.current_wind_speed || 0)} km/h</strong></div></div><div className="weather-days">{weather.daily.map((day) => <div key={day.date}><span>{new Date(day.date).toLocaleDateString(language === 'kn' ? 'kn-IN' : 'en-IN', { weekday: 'short' })}</span><strong>{Math.round(day.maximum_temperature)}°</strong><small>{Math.round(day.precipitation_probability)}% {t('weather.rain')}</small></div>)}</div><small className="weather-source">{weather.source}</small></> : <div className="compact-empty">{t('weather.unavailable')}</div>}
        </article>

        <article className="market-panel news-source-card"><span className="section-kicker">{t('news.sources')}</span><h2>{t('news.sourceTitle')}</h2><p>{t('news.sourceText')}</p><div>{data.sources.slice(0, 8).map((source) => <span key={source}>{source}</span>)}</div><small>{data.note}</small></article>
      </aside>
    </section>
  </>
}
