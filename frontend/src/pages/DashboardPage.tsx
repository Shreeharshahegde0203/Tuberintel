import {
  ArrowRight,
  BarChart3,
  Boxes,
  CloudOff,
  History,
  IndianRupee,
  Landmark,
  MapPin,
  Newspaper,
  PackageCheck,
  ScanLine,
  Snowflake,
  TrendingDown,
  TrendingUp,
  Truck,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAuth } from '../auth/AuthContext'
import { EmptyState, ErrorState, LoadingState, StatusBadge } from '../components/Common'
import { coordinatesFor, readMarketLocation, type MarketLocation } from '../data/marketLocations'
import { useI18n } from '../i18n/I18nContext'
import { getDashboard, getMarketOverview, getNews, getWeather } from '../services/api'
import { actionLabel, formatCurrency, formatDate, formatNumber } from '../services/format'
import type { DashboardSummary, MarketOverview, NewsItem, WeatherResponse } from '../types'

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [market, setMarket] = useState<MarketOverview | null>(null)
  const [weather, setWeather] = useState<WeatherResponse | null>(null)
  const [weatherError, setWeatherError] = useState('')
  const [news, setNews] = useState<NewsItem[]>([])
  const [newsError, setNewsError] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()
  const { language, locale } = useI18n()
  const [location, setLocation] = useState<MarketLocation>(() => readMarketLocation())
  const selectedCoordinates = { ...coordinatesFor(location), label: `${location.city}, ${location.state}` }

  const copy = language === 'kn'
    ? {
        greetingMorning: 'ಶುಭೋದಯ',
        greetingAfternoon: 'ಶುಭ ಮಧ್ಯಾಹ್ನ',
        greetingEvening: 'ಶುಭ ಸಂಜೆ',
        subtitle: 'ಇಂದಿನ ಆಲೂಗಡ್ಡೆ ನಿರ್ಧಾರಗಳಿಗೆ ಬೇಕಾದ ಮುಖ್ಯ ಮಾಹಿತಿ ಒಂದೇ ಸ್ಥಳದಲ್ಲಿ.',
        weather: 'ಹವಾಮಾನ ಮತ್ತು ಬೆಳೆ ಅಪಾಯ',
        weatherPending: 'ಹವಾಮಾನ ಡೇಟಾ ಈ ಹಂತದಲ್ಲಿ ಲಭ್ಯವಿಲ್ಲ.',
        latestNews: 'ಇತ್ತೀಚಿನ ಆಲೂಗಡ್ಡೆ ಮಾಹಿತಿ',
        noNews: 'ಸುದ್ದಿ ಫೀಡ್ ಇನ್ನೂ ಲಭ್ಯವಿಲ್ಲ.',
        modal: 'ಇಂದಿನ ಸರಾಸರಿ ಮಾದರಿ ಬೆಲೆ',
        sevenDay: '7 ದಿನಗಳ ಚಲನೆ',
        bestMarket: 'ಉನ್ನತ ಮಂಡಿ',
        batches: 'ವಿಶ್ಲೇಷಿಸಿದ ಬ್ಯಾಚ್‌ಗಳು',
        quickActions: 'ತ್ವರಿತ ಕಾರ್ಯಗಳು',
        quickText: 'ಮುಖ್ಯ ಸಾಧನಗಳಿಗೆ ನೇರ ಪ್ರವೇಶ',
        quality: 'ಗುಣಮಟ್ಟ ಪರಿಶೀಲನೆ',
        mandi: 'ಮಂಡಿ ಬೆಲೆಗಳು',
        analytics: 'ಬೆಲೆ ವಿಶ್ಲೇಷಣೆ',
        storage: 'ಸಂಗ್ರಹ ನಿರ್ಧಾರ',
        transport: 'ಸಾಗಣೆ ಲೆಕ್ಕ',
        newsAction: 'ಸುದ್ದಿ ಮತ್ತು ಯೋಜನೆಗಳು',
        history: 'ಬ್ಯಾಚ್ ಇತಿಹಾಸ',
        models: 'ಮಾದರಿಗಳು ಮತ್ತು ವಿಧಾನಗಳು',
        topMarkets: 'ಇಂದಿನ ಪ್ರಮುಖ ಮಂಡಿಗಳು',
        priceTrend: 'ಬೆಲೆ ಪ್ರವೃತ್ತಿ',
        recent: 'ಇತ್ತೀಚಿನ ಬ್ಯಾಚ್ ವಿಶ್ಲೇಷಣೆ',
        source: 'ಮೂಲ',
        comingSoon: 'ಮುಂದಿನ ಹಂತ',
        unavailable: 'ಲಭ್ಯವಿಲ್ಲ',
      }
    : {
        greetingMorning: 'Good morning',
        greetingAfternoon: 'Good afternoon',
        greetingEvening: 'Good evening',
        subtitle: 'Everything needed for today’s potato decisions, in one clear workspace.',
        weather: 'Weather & crop risk',
        weatherPending: 'Weather data is unavailable in this phase.',
        latestNews: 'Latest potato intelligence',
        noNews: 'The news feed is not available yet.',
        modal: "Today's average modal price",
        sevenDay: '7-day movement',
        bestMarket: 'Top mandi',
        batches: 'Analysed batches',
        quickActions: 'Quick actions',
        quickText: 'Direct access to the main decision tools',
        quality: 'Quality Check',
        mandi: 'Mandi Prices',
        analytics: 'Price Analytics',
        storage: 'Storage Decision',
        transport: 'Transport Estimate',
        newsAction: 'News & Schemes',
        history: 'Batch History',
        models: 'Models & Methods',
        topMarkets: 'Top mandis today',
        priceTrend: 'Price trend',
        recent: 'Recent batch analyses',
        source: 'Source',
        comingSoon: 'Coming soon',
        unavailable: 'Unavailable',
      }

  useEffect(() => {
    let ignore = false

    async function load() {
      setLoading(true)
      setError('')
      try {
        const [dashboardData, marketData] = await Promise.all([
          getDashboard(),
          getMarketOverview(location.state),
        ])
        if (ignore) return
        setDashboard(dashboardData)
        setMarket(marketData)
      } catch (loadError) {
        if (ignore) return
        const message = loadError instanceof Error ? loadError.message : 'Unable to load dashboard data.'
        setError(message)
      } finally {
        if (!ignore) setLoading(false)
      }

      try {
        const weatherData = await getWeather(selectedCoordinates.latitude, selectedCoordinates.longitude, 5)
        if (!ignore) {
          setWeather(weatherData)
          setWeatherError('')
        }
      } catch (weatherLoadError) {
        if (!ignore) {
          setWeather(null)
          setWeatherError(weatherLoadError instanceof Error ? weatherLoadError.message : 'Weather unavailable.')
        }
      }

      try {
        const newsData = await getNews({ limit: 4 })
        if (!ignore) {
          setNews(newsData.items.length ? newsData.items : newsData.articles || [])
          setNewsError('')
        }
      } catch (newsLoadError) {
        if (!ignore) {
          setNews([])
          setNewsError(newsLoadError instanceof Error ? newsLoadError.message : 'News unavailable.')
        }
      }
    }

    void load()
    return () => {
      ignore = true
    }
  }, [location.city, location.state, selectedCoordinates.latitude, selectedCoordinates.longitude])

  useEffect(() => {
    const listener = (event: Event) => setLocation((event as CustomEvent<MarketLocation>).detail)
    window.addEventListener('tuberintel-location', listener)
    return () => window.removeEventListener('tuberintel-location', listener)
  }, [])

  const hour = new Date().getHours()
  const greeting = hour < 12 ? copy.greetingMorning : hour < 17 ? copy.greetingAfternoon : copy.greetingEvening
  const firstName = user?.name?.split(' ')[0] || 'Farmer'

  const chartData = useMemo(
    () =>
      (market?.forecast || dashboard?.price_forecast || []).map((point) => ({
        ...point,
        label: new Date(point.date).toLocaleDateString(locale, { day: 'numeric', month: 'short' }),
      })),
    [dashboard?.price_forecast, locale, market?.forecast],
  )

  const topMarkets = market?.top_markets || []

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} retry={() => window.location.reload()} />
  if (!dashboard || !market) {
    return (
      <EmptyState
        title="Dashboard unavailable"
        description="The core dashboard response is empty."
        actionLabel="Open mandi prices"
        actionTo="/market"
      />
    )
  }

  const trendNegative = market.change_percent < 0
  const quickActions = [
    { to: '/analyze', title: copy.quality, icon: ScanLine, active: true, tone: 'teal' },
    { to: '/market', title: copy.mandi, icon: Landmark, active: true, tone: 'amber' },
    { title: copy.analytics, icon: BarChart3, active: false, tone: 'blue' },
    { title: copy.storage, icon: Snowflake, active: false, tone: 'cyan' },
    { title: copy.transport, icon: Truck, active: false, tone: 'orange' },
    { title: copy.newsAction, icon: Newspaper, active: false, tone: 'violet' },
    { to: '/history', title: copy.history, icon: History, active: true, tone: 'rose' },
    { to: '/models', title: copy.models, icon: Boxes, active: true, tone: 'indigo' },
  ]

  return (
    <div className="pb-dashboard">
      <section className="pb-dashboard-heading">
        <div>
          <h1>{greeting}, {firstName}</h1>
          <p><MapPin size={16} />{selectedCoordinates.label} · {copy.subtitle}</p>
        </div>
        <Link to="/analyze" className="pb-primary-button">
          <PackageCheck size={18} />
          {copy.quality}
        </Link>
      </section>

      <section className="pb-dashboard-hero-grid">
        <article className="pb-weather-card">
          <div className="pb-weather-copy">
            <span className="pb-card-eyebrow">
              <CloudOff size={16} />
              {copy.weather}
            </span>
            <h2>{weather?.source || copy.unavailable}</h2>
            {weather ? (
              <>
                <div className="pb-weather-temperature">
                  {weather.current.current_temperature == null ? '—' : Math.round(weather.current.current_temperature)}°<small>C</small>
                </div>
                <p>{selectedCoordinates.label}</p>
              </>
            ) : (
              <>
                <div className="pb-weather-temperature pending">—°</div>
                <p>{copy.weatherPending}</p>
              </>
            )}
          </div>
          <div className="pb-weather-art">
            <CloudOff size={88} strokeWidth={1.35} />
            <span>{weatherError || weather?.source || copy.unavailable}</span>
          </div>
        </article>

        <article className="pb-news-rail">
          <div className="pb-card-title-row">
            <div>
              <span>{copy.latestNews}</span>
              <strong>{copy.source}: {news.length ? 'backend feed' : copy.unavailable}</strong>
            </div>
            <Newspaper size={21} />
          </div>
          <div className="pb-news-list">
            {news.length ? news.map((article) => (
              <a href={article.url || '#'} target={article.url ? '_blank' : undefined} rel="noreferrer" key={article.id}>
                <span>{article.category || 'Potato update'}</span>
                <strong>{article.title}</strong>
                <small>{article.source || ''}{article.published_at ? ` · ${formatDate(article.published_at, language)}` : ''}</small>
              </a>
            )) : <div className="pb-news-empty"><Newspaper size={30} /><strong>{copy.noNews}</strong><small>{newsError || copy.comingSoon}</small></div>}
          </div>
        </article>
      </section>

      <section className="pb-market-summary-grid">
        <article><span className="pb-summary-icon green"><IndianRupee size={20} /></span><div><small>{copy.modal}</small><strong>{formatCurrency(dashboard.latest_modal_price, 0, language)} <em>/ qtl</em></strong></div></article>
        <article><span className={`pb-summary-icon ${trendNegative ? 'red' : 'green'}`}>{trendNegative ? <TrendingDown size={20} /> : <TrendingUp size={20} />}</span><div><small>{copy.sevenDay}</small><strong className={trendNegative ? 'negative' : 'positive'}>{market.change_percent >= 0 ? '+' : ''}{market.change_percent.toFixed(1)}%</strong></div></article>
        <article><span className="pb-summary-icon blue"><Landmark size={20} /></span><div><small>{copy.bestMarket}</small><strong>{market.best_market || '—'}</strong></div></article>
        <article><span className="pb-summary-icon amber"><Boxes size={20} /></span><div><small>{copy.batches}</small><strong>{formatNumber(dashboard.analyzed_batches, 0, language)}</strong></div></article>
      </section>

      <section className="pb-section-block">
        <div className="pb-section-heading"><div><h2>{copy.quickActions}</h2><p>{copy.quickText}</p></div></div>
        <div className="pb-quick-grid">
          {quickActions.map(({ to, title, icon: Icon, active, tone }) => active && to ? (
            <Link to={to} className={`pb-quick-card tone-${tone}`} key={title}><span><Icon size={25} strokeWidth={1.8} /></span><strong>{title}</strong><ArrowRight size={17} /></Link>
          ) : (
            <div className={`pb-quick-card disabled tone-${tone}`} key={title}><span><Icon size={25} strokeWidth={1.8} /></span><strong>{title}</strong><small>{copy.comingSoon}</small></div>
          ))}
        </div>
      </section>

      <section className="pb-market-intelligence-grid">
        <article className="pb-panel pb-top-markets-panel">
          <div className="pb-panel-heading"><div><h2>{copy.topMarkets}</h2><p>{location.state}</p></div><Link to="/market">View all<ArrowRight size={16} /></Link></div>
          <div className="pb-top-market-list">
            {topMarkets.length ? topMarkets.slice(0, 5).map((item) => <div key={`${item.market}-${item.rank}`}><span>{item.rank}</span><div><strong>{item.market}</strong><small>{item.district} · {item.variety}</small></div><div><strong>{formatCurrency(item.modal_price, 0, language)}</strong><small>/ qtl</small></div></div>) : <div className="pb-empty-row"><Landmark size={30} /><strong>No market data yet.</strong></div>}
          </div>
        </article>

        <article className="pb-panel pb-price-chart-panel">
          <div className="pb-panel-heading"><div><h2>{copy.priceTrend}</h2><p>{location.state}</p></div><Link to="/market">View all<ArrowRight size={16} /></Link></div>
          <div className="pb-price-chart">
            {chartData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 8, right: 12, left: -10, bottom: 0 }}>
                  <defs>
                    <linearGradient id="pbPriceFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#20a873" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="#20a873" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#e4ece8" />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} />
                  <YAxis axisLine={false} tickLine={false} tickFormatter={(value: number | string) => `₹${Math.round(Number(value))}`} />
                  <Tooltip formatter={tooltipFormatter(language)} />
                  <Area type="monotone" dataKey="predicted_price" stroke="#17a36e" strokeWidth={2.5} fill="url(#pbPriceFill)" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="pb-empty-row"><BarChart3 size={30} /><strong>No backend trend data is available yet.</strong></div>
            )}
          </div>
        </article>
      </section>

      <section className="pb-panel pb-recent-panel">
        <div className="pb-panel-heading"><div><h2>{copy.recent}</h2><p>{dashboard.recent_batches.length} {copy.batches.toLowerCase()}</p></div><Link to="/history">View all<ArrowRight size={16} /></Link></div>
        {dashboard.recent_batches.length ? (
          <div className="pb-table-wrap"><table><thead><tr><th>Batch</th><th>Origin</th><th>Quality</th><th>Decision</th><th>Expected profit</th><th /></tr></thead><tbody>{dashboard.recent_batches.slice(0, 5).map((batch) => <tr key={batch.id}><td><strong>{batch.batch_code}</strong><small>{batch.variety} · {formatDate(batch.created_at, language)}</small></td><td>{batch.source_location}</td><td>{batch.grade ? <span className={`grade-token grade-${batch.grade.toLowerCase()}`}>{batch.grade}</span> : '—'}</td><td><StatusBadge value={batch.action ? actionLabel(batch.action, language) : batch.status} /></td><td>{batch.expected_net_profit == null ? '—' : formatCurrency(batch.expected_net_profit, 0, language)}</td><td><Link to={`/batches/${batch.id}`}><ArrowRight size={18} /></Link></td></tr>)}</tbody></table></div>
        ) : <EmptyState title="No batch analyses yet" description="Start a quality check to populate the dashboard." actionLabel="Open Quality Check" actionTo="/analyze" />}
      </section>
    </div>
  )
}

function tooltipFormatter(language: 'en' | 'kn') {
  return (value: number | string | ReadonlyArray<number | string> | undefined) => {
    const raw = Array.isArray(value) ? value[0] : value
    if (raw == null) return ['—', language === 'kn' ? 'ಬೆಲೆ' : 'Price']
    return [formatCurrency(Number(raw), 0, language), language === 'kn' ? 'ಬೆಲೆ' : 'Price']
  }
}
