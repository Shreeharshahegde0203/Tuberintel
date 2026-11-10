import {
  ArrowRight,
  BarChart3,
  CloudRain,
  Droplets,
  Landmark,
  MapPin,
  Newspaper,
  PackageCheck,
  SearchCheck,
  ShoppingCart,
  ThermometerSun,
  TrendingDown,
  TrendingUp,
  Wind,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { ErrorState, LoadingState, StatusBadge } from '../components/Common'
import { useI18n } from '../i18n/I18nContext'
import { api, getDashboard, getMarketOverview } from '../services/api'
import { actionLabel, formatCurrency, formatDate, formatNumber } from '../services/format'
import type { DashboardSummary, MarketOverview } from '../types'
import { coordinatesFor, readMarketLocation, type MarketLocation } from '../data/marketLocations'

type WeatherData = {
  current_temperature: number | null
  current_humidity: number | null
  current_wind_speed: number | null
  current_weather_code: number | null
  daily: Array<{ date: string; minimum_temperature: number; maximum_temperature: number; precipitation_probability: number }>
  source: string
  fetched_at?: string
}

type NewsArticle = {
  id: number | string
  title: string
  category?: string
  source?: string
  published_at?: string | null
  url?: string
}

type NewsData = { articles: NewsArticle[] }

function weatherLabel(code: number | null, language: 'en' | 'kn') {
  if (code == null) return language === 'kn' ? 'ಲಭ್ಯವಿಲ್ಲ' : 'Unavailable'
  if ([0, 1].includes(code)) return language === 'kn' ? 'ಸ್ವಚ್ಛ' : 'Clear'
  if ([2, 3].includes(code)) return language === 'kn' ? 'ಮೋಡ ಕವಿದಿದೆ' : 'Cloudy'
  if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) return language === 'kn' ? 'ಮಳೆಯ ಸಾಧ್ಯತೆ' : 'Rain likely'
  return language === 'kn' ? 'ಬದಲಾಗುವ ಹವಾಮಾನ' : 'Variable'
}

function riskFromWeather(weather: WeatherData | null, language: 'en' | 'kn') {
  const humidity = weather?.current_humidity ?? null
  const rain = weather?.daily?.[0]?.precipitation_probability ?? null
  if (humidity == null && rain == null) {
    return { level: language === 'kn' ? 'ಲಭ್ಯವಿಲ್ಲ' : 'Unavailable', tone: 'neutral', reason: language === 'kn' ? 'ಹವಾಮಾನ ಮಾಹಿತಿ ಇಲ್ಲ' : 'Weather data unavailable' }
  }
  if ((rain ?? 0) >= 60 || (humidity ?? 0) >= 85) {
    return { level: language === 'kn' ? 'ಹೆಚ್ಚು' : 'High', tone: 'danger', reason: language === 'kn' ? 'ಹೆಚ್ಚಿನ ತೇವಾಂಶ ಅಥವಾ ಮಳೆಯ ಸಾಧ್ಯತೆ' : 'High humidity or rain probability' }
  }
  if ((rain ?? 0) >= 30 || (humidity ?? 0) >= 72) {
    return { level: language === 'kn' ? 'ಮಧ್ಯಮ' : 'Moderate', tone: 'warning', reason: language === 'kn' ? 'ತೇವಾಂಶ / ಮಳೆಯ ಮೇಲ್ವಿಚಾರಣೆ ಅಗತ್ಯ' : 'Monitor humidity and rain' }
  }
  return { level: language === 'kn' ? 'ಕಡಿಮೆ' : 'Low', tone: 'positive', reason: language === 'kn' ? 'ತಕ್ಷಣದ ಪ್ರಮುಖ ಹವಾಮಾನ ಅಪಾಯ ಇಲ್ಲ' : 'No major immediate weather signal' }
}

export default function DashboardPage() {
  const [dashboard, setDashboard] = useState<DashboardSummary | null>(null)
  const [market, setMarket] = useState<MarketOverview | null>(null)
  const [weather, setWeather] = useState<WeatherData | null>(null)
  const [news, setNews] = useState<NewsArticle[]>([])
  const [error, setError] = useState('')
  const { language, locale } = useI18n()
  const [location, setLocation] = useState<MarketLocation>(() => readMarketLocation())
  const state = location.state
  const selectedCoordinates = { ...coordinatesFor(location), label: `${location.district || location.market || location.state}, ${location.state}` }

  const copy = language === 'kn'
    ? {
        overview: 'ಅವಲೋಕನ', updated: 'ಕೊನೆಯ ನವೀಕರಣ', runQuality: 'ಗುಣಮಟ್ಟ ಪರಿಶೀಲನೆ', marketPrices: 'ಮಂಡಿ ಬೆಲೆಗಳು', batches: 'ಬ್ಯಾಚ್‌ಗಳು', marketplace: 'ಖರೀದಿ / ಮಾರಾಟ',
        marketSource: 'ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು', weatherSource: 'ಹವಾಮಾನ', demo: 'ಪ್ರದರ್ಶನ ಡೇಟಾ', live: 'AGMARKNET',
        snapshot: 'ಇಂದಿನ ನಿರ್ಧಾರ ಸಾರಾಂಶ', modalPrice: 'ಆಯ್ದ ಮಂಡಿ ಮಾದರಿ ಬೆಲೆ', movement: '7 ದಿನದ ಬೆಲೆ ಚಲನೆ', handlingRisk: 'ಹವಾಮಾನ / ಹ್ಯಾಂಡ್ಲಿಂಗ್ ಅಪಾಯ', latestBatch: 'ಇತ್ತೀಚಿನ ವಿಶ್ಲೇಷಿತ ಬ್ಯಾಚ್', recommendation: 'ಶಿಫಾರಸು',
        noBatch: 'ವಿಶ್ಲೇಷಿತ ಬ್ಯಾಚ್ ಇಲ್ಲ', noRecommendation: 'ಶಿಫಾರಸು ಇಲ್ಲ', perQtl: '/ ಕ್ವಿಂಟಲ್',
        priceSignal: '30 ದಿನದ ಬೆಲೆ ಸೂಚನೆ', advisory: 'ಮಾರುಕಟ್ಟೆ ಬೆಲೆ ಇತಿಹಾಸದ ಆಧಾರದ ಸಲಹಾ ಸೂಚನೆ', drivers: 'ನಿರ್ಧಾರ ಚಾಲಕರು', priceTrend: 'ಬೆಲೆ ಪ್ರವೃತ್ತಿ', latestQuality: 'ಇತ್ತೀಚಿನ ಗುಣಮಟ್ಟ', spread: 'ಮಂಡಿ ಬೆಲೆ ವ್ಯತ್ಯಾಸ', weather: 'ಹವಾಮಾನ ಮತ್ತು ಹ್ಯಾಂಡ್ಲಿಂಗ್',
        latestBatchTitle: 'ಇತ್ತೀಚಿನ ಬ್ಯಾಚ್', viewAnalysis: 'ವಿಶ್ಲೇಷಣೆ ನೋಡಿ', createSell: 'ಮಾರಾಟ ಪೋಸ್ಟ್ ರಚಿಸಿ', quantity: 'ಪ್ರಮಾಣ', grade: 'ಗ್ರೇಡ್', quality: 'ಗುಣಮಟ್ಟ', decision: 'ನಿರ್ಧಾರ', created: 'ರಚಿಸಲಾಗಿದೆ',
        nearby: 'ಇತ್ತೀಚಿನ ಮಂಡಿ ಬೆಲೆಗಳು', mandi: 'ಮಂಡಿ', district: 'ಜಿಲ್ಲೆ', variety: 'ತಳಿ', modal: 'ಮಾದರಿ ₹/ಕ್ವಿಂಟಲ್', updatedCol: 'ದಿನಾಂಕ', viewAll: 'ಎಲ್ಲ ನೋಡಿ',
        intelligence: 'ಇತ್ತೀಚಿನ ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ', noNews: 'ಸುದ್ದಿ ಮೂಲ ಸಂಪರ್ಕಗೊಂಡಿಲ್ಲ.', configureNews: 'ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ ಪುಟದಲ್ಲಿ ಮೂಲಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.',
        weatherContext: 'ಹವಾಮಾನ ಮತ್ತು ಹ್ಯಾಂಡ್ಲಿಂಗ್', humidity: 'ಆರ್ದ್ರತೆ', rain: 'ಮಳೆ', wind: 'ಗಾಳಿ', source: 'ಮೂಲ',
      }
    : {
        overview: 'Overview', updated: 'Last updated', runQuality: 'Run quality check', marketPrices: 'Mandi prices', batches: 'Batches', marketplace: 'Buy / Sell',
        marketSource: 'Market prices', weatherSource: 'Weather', demo: 'Demonstration data', live: 'AGMARKNET',
        snapshot: "Today's decision snapshot", modalPrice: 'Selected mandi modal price', movement: '7-day price movement', handlingRisk: 'Weather / handling risk', latestBatch: 'Latest analysed batch', recommendation: 'Recommended action',
        noBatch: 'No batch analysed', noRecommendation: 'No recommendation', perQtl: '/ qtl',
        priceSignal: '30-day price signal', advisory: 'Advisory signal from available market-price history', drivers: 'Decision drivers', priceTrend: 'Price trend', latestQuality: 'Latest quality', spread: 'Mandi price spread', weather: 'Weather & handling',
        latestBatchTitle: 'Latest batch', viewAnalysis: 'View analysis', createSell: 'Create sell listing', quantity: 'Quantity', grade: 'Grade', quality: 'Quality', decision: 'Decision', created: 'Created',
        nearby: 'Latest mandi prices', mandi: 'Mandi', district: 'District', variety: 'Variety', modal: 'Modal ₹/qtl', updatedCol: 'Date', viewAll: 'View all',
        intelligence: 'Latest market intelligence', noNews: "News feed isn't connected.", configureNews: 'Review configured sources in Market intelligence.',
        weatherContext: 'Weather & handling', humidity: 'Humidity', rain: 'Rain', wind: 'Wind', source: 'Source',
      }

  const load = async () => {
    setError('')
    try {
      const [dashboardData, marketData] = await Promise.all([getDashboard(), getMarketOverview(state)])
      setDashboard(dashboardData)
      setMarket(marketData)

      const [weatherResult, newsResult] = await Promise.allSettled([
        api.get<WeatherData>('/weather', { params: { latitude: selectedCoordinates.latitude, longitude: selectedCoordinates.longitude, days: 5 } }),
        api.get<NewsData>('/news', { params: { limit: 5 } }),
      ])
      if (weatherResult.status === 'fulfilled') setWeather(weatherResult.value.data)
      if (newsResult.status === 'fulfilled') setNews(newsResult.value.data.articles || [])
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message)
    }
  }

  useEffect(() => { void load() }, [state, location.district, location.market])
  useEffect(() => {
    const listener = (event: Event) => setLocation((event as CustomEvent<MarketLocation>).detail)
    window.addEventListener('tuberintel-location', listener)
    return () => window.removeEventListener('tuberintel-location', listener)
  }, [])

  const chartData = useMemo(() => {
    const forecast = market?.forecast?.length ? market.forecast : dashboard?.price_forecast || []
    return forecast.slice(0, 30).map((point) => ({ ...point, label: new Date(point.date).toLocaleDateString(locale, { day: 'numeric', month: 'short' }) }))
  }, [dashboard?.price_forecast, market?.forecast, locale])

  const topMarkets = useMemo(() => {
    if (!market) return []
    const latest = [...market.latest_prices]
    latest.sort((a, b) => b.modal_price - a.modal_price)
    return latest.slice(0, 6)
  }, [market])

  if (error) return <ErrorState message={String(error)} retry={() => void load()} />
  if (!dashboard || !market) return <LoadingState />

  const selectedPrice = market.latest_prices.find((item) => item.market === location.market) || market.latest_prices[0]
  const latestBatch = dashboard.recent_batches[0] || null
  const weatherRisk = riskFromWeather(weather, language)
  const rain = weather?.daily?.[0]?.precipitation_probability ?? null
  const spreadValues = topMarkets.map((item) => item.modal_price).filter((value) => Number.isFinite(value))
  const mandiSpread = spreadValues.length > 1 ? Math.max(...spreadValues) - Math.min(...spreadValues) : null
  const marketUpdated = market.last_sync?.finished_at || market.last_sync?.started_at || selectedPrice?.fetched_at || null
  const marketLabel = location.market || location.district || location.state

  return (
    <div className="ops-dashboard">
      <header className="ops-page-header ops-overview-header">
        <div>
          <h1>{copy.overview}</h1>
          <p><MapPin size={15} />{marketLabel}{location.district ? ` · ${location.district}, ${location.state}` : ` · ${location.state}`}{marketUpdated ? ` · ${copy.updated} ${formatDate(marketUpdated, language)}` : ''}</p>
        </div>
        <div className="ops-page-actions">
          <Link className="button button-secondary" to="/market"><Landmark size={17} />{copy.marketPrices}</Link>
          <Link className="button button-primary" to="/analyze"><PackageCheck size={17} />{copy.runQuality}</Link>
        </div>
      </header>

      <section className="ops-source-strip" aria-label="Data sources">
        <div><span className={`ops-source-dot ${market.live_data ? 'live' : 'demo'}`} /><strong>{copy.marketSource}:</strong><span>{market.live_data ? copy.live : copy.demo}</span><small>{market.freshness}</small></div>
        <div><span className={`ops-source-dot ${weather ? 'live' : ''}`} /><strong>{copy.weatherSource}:</strong><span>{weather?.source || (language === 'kn' ? 'ಲಭ್ಯವಿಲ್ಲ' : 'Unavailable')}</span>{weather?.fetched_at && <small>{formatDate(weather.fetched_at, language)}</small>}</div>
      </section>

      <section className="ops-section">
        <div className="ops-section-head"><h2>{copy.snapshot}</h2></div>
        <div className="ops-snapshot-panel">
          <article>
            <span>{copy.modalPrice}</span>
            <strong>{selectedPrice ? formatCurrency(selectedPrice.modal_price, 0, language) : formatCurrency(dashboard.latest_modal_price, 0, language)} <small>{copy.perQtl}</small></strong>
            <small>{selectedPrice?.market || marketLabel}</small>
          </article>
          <article>
            <span>{copy.movement}</span>
            <strong className={market.change_percent < 0 ? 'negative' : 'positive'}>{market.change_percent >= 0 ? '+' : ''}{market.change_percent.toFixed(1)}%</strong>
            <small>{market.price_direction}</small>
          </article>
          <article>
            <span>{copy.handlingRisk}</span>
            <strong className={`ops-risk-text ${weatherRisk.tone}`}>{weatherRisk.level}</strong>
            <small>{weatherRisk.reason}</small>
          </article>
          <article>
            <span>{copy.latestBatch}</span>
            <strong>{latestBatch?.grade ? `Grade ${latestBatch.grade}` : copy.noBatch}</strong>
            <small>{latestBatch?.quality_score != null ? `${latestBatch.quality_score.toFixed(1)}/100 · ${latestBatch.batch_code}` : latestBatch?.batch_code || '—'}</small>
          </article>
          <article>
            <span>{copy.recommendation}</span>
            <strong>{latestBatch?.action ? actionLabel(latestBatch.action, language) : copy.noRecommendation}</strong>
            <small>{latestBatch?.expected_net_profit != null ? formatCurrency(latestBatch.expected_net_profit, 0, language) : '—'}</small>
          </article>
        </div>
      </section>

      <section className="ops-dashboard-grid ops-grid-8-4">
        <article className="ops-panel ops-chart-panel">
          <div className="ops-panel-head">
            <div><h2>{copy.priceSignal}</h2><p>{copy.advisory}</p></div>
            <Link to="/analytics">{copy.viewAll}<ArrowRight size={15} /></Link>
          </div>
          <div className="ops-chart-wrap">
            {chartData.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ top: 12, right: 18, left: 4, bottom: 2 }}>
                  <CartesianGrid vertical={false} stroke="#e5e9e5" />
                  <XAxis dataKey="label" axisLine={false} tickLine={false} minTickGap={22} />
                  <YAxis axisLine={false} tickLine={false} width={62} tickFormatter={(value) => `₹${Math.round(Number(value))}`} />
                  <Tooltip formatter={(value) => [formatCurrency(Number(value), 0, language), copy.priceSignal]} />
                  <Line type="monotone" dataKey="predicted_price" stroke="#176b45" strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : <div className="ops-compact-empty">{language === 'kn' ? 'ಬೆಲೆ ಸೂಚನೆಗೆ ಸಾಕಷ್ಟು ಡೇಟಾ ಇಲ್ಲ.' : 'Not enough price history for a signal.'}</div>}
          </div>
          <div className="ops-chart-source">{copy.source}: {market.source_note}</div>
        </article>

        <article className="ops-panel ops-driver-panel">
          <div className="ops-panel-head"><div><h2>{copy.drivers}</h2><p>{selectedCoordinates.label}</p></div></div>
          <div className="ops-driver-list">
            <div><span><BarChart3 size={17} />{copy.priceTrend}</span><strong className={market.change_percent < 0 ? 'negative' : 'positive'}>{market.change_percent >= 0 ? '+' : ''}{market.change_percent.toFixed(1)}%</strong><small>{market.price_direction}</small></div>
            <div><span><ThermometerSun size={17} />{copy.weather}</span><strong className={`ops-risk-text ${weatherRisk.tone}`}>{weatherRisk.level}</strong><small>{weatherRisk.reason}</small></div>
            <div><span><SearchCheck size={17} />{copy.latestQuality}</span><strong>{latestBatch?.grade ? `Grade ${latestBatch.grade}` : '—'}</strong><small>{latestBatch?.quality_score != null ? `${latestBatch.quality_score.toFixed(1)}/100` : copy.noBatch}</small></div>
            <div><span><Landmark size={17} />{copy.spread}</span><strong>{mandiSpread == null ? '—' : formatCurrency(mandiSpread, 0, language)}</strong><small>{topMarkets.length} {language === 'kn' ? 'ಮಂಡಿಗಳು' : 'mandis compared'}</small></div>
          </div>
        </article>
      </section>

      <section className="ops-dashboard-grid ops-grid-7-5">
        <article className="ops-panel ops-latest-batch-panel">
          <div className="ops-panel-head"><div><h2>{copy.latestBatchTitle}</h2><p>{latestBatch ? latestBatch.batch_code : copy.noBatch}</p></div>{latestBatch && <Link to={`/batches/${latestBatch.id}`}>{copy.viewAnalysis}<ArrowRight size={15} /></Link>}</div>
          {latestBatch ? (
            <>
              <div className="ops-batch-facts">
                <div><span>{copy.quantity}</span><strong>{formatNumber(latestBatch.quantity_kg, 0, language)} kg</strong></div>
                <div><span>{copy.grade}</span><strong>{latestBatch.grade || '—'}</strong></div>
                <div><span>{copy.quality}</span><strong>{latestBatch.quality_score == null ? '—' : `${latestBatch.quality_score.toFixed(1)}/100`}</strong></div>
                <div><span>{copy.decision}</span><strong>{latestBatch.action ? actionLabel(latestBatch.action, language) : '—'}</strong></div>
                <div><span>{copy.created}</span><strong>{formatDate(latestBatch.created_at, language)}</strong></div>
              </div>
              <div className="ops-inline-actions"><Link to={`/batches/${latestBatch.id}`} className="button button-secondary">{copy.viewAnalysis}</Link><Link to="/trade" className="button button-secondary"><ShoppingCart size={16} />{copy.createSell}</Link></div>
            </>
          ) : <div className="ops-compact-empty"><span>{copy.noBatch}</span><Link to="/analyze">{copy.runQuality}<ArrowRight size={15} /></Link></div>}
        </article>

        <article className="ops-panel ops-mandi-panel">
          <div className="ops-panel-head"><div><h2>{copy.nearby}</h2><p>{location.state}</p></div><Link to="/market">{copy.viewAll}<ArrowRight size={15} /></Link></div>
          <div className="ops-table-scroll">
            <table className="ops-compact-table">
              <thead><tr><th>{copy.mandi}</th><th>{copy.variety}</th><th>{copy.modal}</th><th>{copy.updatedCol}</th></tr></thead>
              <tbody>{topMarkets.slice(0, 5).map((item) => <tr key={`${item.market}-${item.variety}-${item.arrival_date}`}><td><strong>{item.market}</strong><small>{item.district}</small></td><td>{item.variety}</td><td>{formatCurrency(item.modal_price, 0, language)}</td><td>{formatDate(item.arrival_date, language)}</td></tr>)}</tbody>
            </table>
          </div>
        </article>
      </section>

      <section className="ops-dashboard-grid ops-grid-8-4 ops-dashboard-bottom">
        <article className="ops-panel ops-news-panel">
          <div className="ops-panel-head"><div><h2>{copy.intelligence}</h2><p>{news.length ? `${news.length} ${language === 'kn' ? 'ನವೀಕರಣಗಳು' : 'recent updates'}` : copy.noNews}</p></div><Link to="/news">{copy.viewAll}<ArrowRight size={15} /></Link></div>
          {news.length ? <div className="ops-news-list">{news.slice(0, 5).map((article) => (
            <a href={article.url || '#'} target={article.url ? '_blank' : undefined} rel="noreferrer" key={article.id}>
              <span>{article.category || (language === 'kn' ? 'ಮಾರುಕಟ್ಟೆ' : 'Market')}</span>
              <strong
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
                </strong>
              <small>{article.source || ''}{article.published_at ? ` · ${formatDate(article.published_at, language)}` : ''}</small>
            </a>
          ))}</div> : <div className="ops-compact-empty"><strong>{copy.noNews}</strong><span>{copy.configureNews}</span></div>}
        </article>

        <article className="ops-panel ops-weather-panel">
          <div className="ops-panel-head"><div><h2>{copy.weatherContext}</h2><p>{weather?.source || 'Open-Meteo'}</p></div>{(rain ?? 0) >= 50 ? <CloudRain size={20} /> : <ThermometerSun size={20} />}</div>
          <div className="ops-weather-current"><strong>{weather?.current_temperature == null ? '—' : `${Math.round(weather.current_temperature)}°C`}</strong><span>{weatherLabel(weather?.current_weather_code ?? null, language)}</span></div>
          <div className="ops-weather-facts">
            <div><Droplets size={16} /><span>{copy.humidity}</span><strong>{weather?.current_humidity == null ? '—' : `${Math.round(weather.current_humidity)}%`}</strong></div>
            <div><CloudRain size={16} /><span>{copy.rain}</span><strong>{rain == null ? '—' : `${Math.round(rain)}%`}</strong></div>
            <div><Wind size={16} /><span>{copy.wind}</span><strong>{weather?.current_wind_speed == null ? '—' : `${Math.round(weather.current_wind_speed)} km/h`}</strong></div>
          </div>
          <p className="ops-weather-note"><span className={`ops-risk-mark ${weatherRisk.tone}`} />{weatherRisk.reason}</p>
        </article>
      </section>
    </div>
  )
}
