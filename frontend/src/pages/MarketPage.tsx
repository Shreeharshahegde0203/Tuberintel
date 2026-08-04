import {
  AlertCircle,
  Building2,
  CalendarDays,
  Database,
  IndianRupee,
  Landmark,
  MapPin,
  RefreshCw,
  Search,
  SlidersHorizontal,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { EmptyState, ErrorState, LoadingState } from '../components/Common'
import { persistMarketLocation, readMarketLocation } from '../data/marketLocations'
import { useI18n } from '../i18n/I18nContext'
import {
  getMandiDirectory,
  getMandiDistricts,
  getMandiStates,
  getMarketAnalytics,
  getMarketFilters,
  getMarketOverview,
  getMarketPrices,
  refreshMarket,
} from '../services/api'
import { formatCurrency, formatDate } from '../services/format'
import type { MandiDirectoryItem, MarketAnalytics, MarketDistrictOption, MarketFilters, MarketOverview, MarketPrice, MarketStateOption } from '../types'

const tileTones = ['mint', 'amber', 'blue', 'rose', 'cyan', 'lime']

export default function MarketPage() {
  const initialLocation = readMarketLocation()
  const [selectedState, setSelectedState] = useState(initialLocation.state)
  const [selectedDistrict, setSelectedDistrict] = useState(initialLocation.city)
  const [selectedMarket, setSelectedMarket] = useState(initialLocation.market || '')
  const [selectedVariety, setSelectedVariety] = useState('')
  const [query, setQuery] = useState('')
  const [stateOptions, setStateOptions] = useState<MarketStateOption[]>([])
  const [districtOptions, setDistrictOptions] = useState<MarketDistrictOption[]>([])
  const [directory, setDirectory] = useState<MandiDirectoryItem[]>([])
  const [overview, setOverview] = useState<MarketOverview | null>(null)
  const [filters, setFilters] = useState<MarketFilters | null>(null)
  const [prices, setPrices] = useState<MarketPrice[]>([])
  const [analytics, setAnalytics] = useState<MarketAnalytics | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [message, setMessage] = useState('')
  const { language } = useI18n()

  const copy = language === 'kn'
    ? {
        title: 'ಮಂಡಿ ಬೆಲೆಗಳು',
        subtitle: 'ಬ್ಯಾಕೆಂಡ್‌ನಿಂದ ಲೋಡ್ ಆಗುವ ನೈಜ ಮಾರುಕಟ್ಟೆ ಡೈರೆಕ್ಟರಿ ಮತ್ತು ಬೆಲೆ ವರದಿ.',
        sourceLabel: 'ಡೇಟಾ ಮೂಲ',
        report: 'ಏಕೀಕೃತ ವರದಿ',
        popular: 'ಮುಖ್ಯ ಮಂಡಿಗಳು',
        directory: 'ಮಾರುಕಟ್ಟೆ ಡೈರೆಕ್ಟರಿ',
        explore: 'ಮಾರುಕಟ್ಟೆ ಅನ್ವೇಷಿಸಿ',
        state: 'ರಾಜ್ಯ',
        district: 'ಜಿಲ್ಲೆ / ನಗರ',
        market: 'ಎಪಿಎಂಸಿ / ಮಂಡಿ',
        variety: 'ತಳಿ',
        fetch: 'ಬೆಲೆಗಳನ್ನು ಅನ್ವಯಿಸಿ',
        refresh: 'ಡೇಟಾ ನವೀಕರಿಸಿ',
        refreshing: 'ನವೀಕರಿಸಲಾಗುತ್ತಿದೆ…',
        records: 'ಬೆಲೆ ದಾಖಲೆಗಳು',
        updated: 'ನವೀಕರಿಸಲಾಗಿದೆ',
        source: 'ಮೂಲ',
        empty: 'ಈ ಆಯ್ಕೆಗಾಗಿ ಮಾರುಕಟ್ಟೆ ಬೆಲೆಗಳು ಲಭ್ಯವಿಲ್ಲ.',
        analytics: 'ಬೆಲೆ ವಿಶ್ಲೇಷಣೆ',
      }
    : {
        title: 'Mandi Prices',
        subtitle: 'A backend-driven market directory and price report for potato decisions.',
        sourceLabel: 'Data source',
        report: 'Consolidated report',
        popular: 'Top mandis',
        directory: 'Market directory',
        explore: 'Explore markets',
        state: 'State',
        district: 'District / city',
        market: 'APMC / market',
        variety: 'Variety',
        fetch: 'Apply filters',
        refresh: 'Refresh data',
        refreshing: 'Refreshing…',
        records: 'Price records',
        updated: 'Updated',
        source: 'Source',
        empty: 'No mandi prices are available for this selection.',
        analytics: 'Price analytics',
      }

  useEffect(() => {
    void getMandiStates().then(setStateOptions).catch(() => setStateOptions([]))
  }, [])

  useEffect(() => {
    let ignore = false
    void getMandiDistricts(selectedState)
      .then((result) => {
        if (!ignore) setDistrictOptions(result)
      })
      .catch(() => {
        if (!ignore) setDistrictOptions([])
      })
    return () => {
      ignore = true
    }
  }, [selectedState])

  useEffect(() => {
    let ignore = false
    void getMandiDirectory(selectedState, selectedDistrict || undefined, query || undefined, 40, 0)
      .then((result) => {
        if (!ignore) setDirectory(result.items)
      })
      .catch(() => {
        if (!ignore) setDirectory([])
      })
    return () => {
      ignore = true
    }
  }, [query, selectedDistrict, selectedState])

  useEffect(() => {
    let ignore = false
    async function loadMarket() {
      setLoading(true)
      setError('')
      try {
        const [overviewData, filterData, priceData, analyticsData] = await Promise.all([
          getMarketOverview(selectedState),
          getMarketFilters(selectedState, selectedDistrict || undefined),
          getMarketPrices({
            state: selectedState,
            district: selectedDistrict || undefined,
            market: selectedMarket || undefined,
            variety: selectedVariety || undefined,
            latest_only: true,
            limit: 100,
          }),
          getMarketAnalytics({
            state: selectedState,
            district: selectedDistrict || undefined,
            market: selectedMarket || undefined,
            variety: selectedVariety || undefined,
            window_days: 30,
          }),
        ])
        if (ignore) return
        setOverview(overviewData)
        setFilters(filterData)
        setPrices(priceData)
        setAnalytics(analyticsData)
      } catch (loadError) {
        if (!ignore) setError(loadError instanceof Error ? loadError.message : 'Unable to load market data.')
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    void loadMarket()
    return () => {
      ignore = true
    }
  }, [selectedDistrict, selectedMarket, selectedState, selectedVariety])

  const visiblePrices = useMemo(() => {
    const searchTerm = query.trim().toLowerCase()
    if (!searchTerm) return prices
    return prices.filter((row) => `${row.market} ${row.district} ${row.variety}`.toLowerCase().includes(searchTerm))
  }, [prices, query])

  const applyLocation = () => {
    persistMarketLocation({ state: selectedState, city: selectedDistrict, market: selectedMarket })
  }

  const chooseLocation = (state: string, district: string, market: string) => {
    setSelectedState(state)
    setSelectedDistrict(district)
    setSelectedMarket(market)
    persistMarketLocation({ state, city: district, market })
  }

  const runRefresh = async () => {
    setRefreshing(true)
    setMessage('')
    try {
      const result = await refreshMarket(selectedState)
      setMessage(`${result.note} ${result.inserted}/${result.received} records updated.`)
    } catch (refreshError) {
      setMessage(refreshError instanceof Error ? refreshError.message : 'Refresh failed.')
    } finally {
      setRefreshing(false)
    }
  }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} retry={() => window.location.reload()} />
  if (!overview || !filters) {
    return <EmptyState title="Market data unavailable" description="The market overview response is empty." />
  }

  const report = overview.consolidated
  const DirectionIcon = report.direction === 'falling' ? TrendingDown : TrendingUp

  return (
    <div className="pb-market-page">
      <section className="pb-market-title-row">
        <div>
          <span className="pb-market-kicker"><Landmark size={16} />{copy.sourceLabel}</span>
          <h1>{copy.title}</h1>
          <p>{copy.subtitle}</p>
        </div>
        <div className={`pb-live-source ${overview.live_data ? 'live' : 'demo'}`}>
          <span />
          <div>
            <strong>{overview.live_data ? 'AGMARKNET / data.gov.in' : 'Cached market data'}</strong>
            <small>{copy.updated}: {overview.freshness}</small>
          </div>
          <Database size={19} />
        </div>
      </section>

      {message && <div className="pb-market-message"><AlertCircle size={18} /><span>{message}</span></div>}

      <section className="pb-market-overview-layout">
        <article className="pb-consolidated-report">
          <div className="pb-report-heading">
            <div>
              <span>{copy.report}</span>
              <h2>{selectedState}{selectedDistrict ? ` · ${selectedDistrict}` : ''}</h2>
              <p>{report.data_source}</p>
            </div>
          </div>
          <div className="pb-report-metrics">
            <div><span className="pb-metric-icon mint"><CalendarDays size={20} /></span><small>Date</small><strong>{report.date ? formatDate(report.date, language) : '—'}</strong></div>
            <div><span className="pb-metric-icon blue"><Building2 size={20} /></span><small>Active mandis</small><strong>{report.active_mandis}</strong></div>
            <div><span className="pb-metric-icon amber"><Landmark size={20} /></span><small>{copy.records}</small><strong>{report.records}</strong></div>
            <div><span className="pb-metric-icon green"><IndianRupee size={20} /></span><small>Average modal</small><strong>{report.average_modal_price == null ? '—' : formatCurrency(report.average_modal_price, 0, language)}</strong></div>
          </div>
          <div className="pb-report-footer">
            <div><span>Range</span><strong>{report.minimum_price == null || report.maximum_price == null ? '—' : `${formatCurrency(report.minimum_price, 0, language)} – ${formatCurrency(report.maximum_price, 0, language)}`}</strong></div>
            <div className={report.change_percent_7d < 0 ? 'negative' : 'positive'}><DirectionIcon size={18} /><span>7D</span><strong>{report.change_percent_7d >= 0 ? '+' : ''}{report.change_percent_7d.toFixed(1)}%</strong></div>
            <button type="button" onClick={runRefresh} disabled={refreshing}><RefreshCw className={refreshing ? 'spin' : ''} size={17} />{refreshing ? copy.refreshing : copy.refresh}</button>
          </div>
        </article>

        <aside className="pb-popular-rail">
          <div className="pb-popular-rail-heading"><div><span>{copy.popular}</span><small>{selectedState}</small></div><em>{overview.live_data ? 'LIVE' : 'CACHE'}</em></div>
          <div className="pb-popular-rail-list">
            {overview.top_markets.slice(0, 6).map((item, index) => (
              <button type="button" key={`${item.market}-${item.rank}`} onClick={() => chooseLocation(item.state, item.district, item.market)}>
                <span className={`pb-mandi-avatar tone-${tileTones[index % tileTones.length]}`}><Landmark size={18} /></span>
                <span><strong>{item.market}</strong><small>{item.district}</small></span>
              </button>
            ))}
          </div>
        </aside>
      </section>

      <section className="pb-market-explorer">
        <div className="pb-explorer-heading"><span className="pb-explorer-icon"><Search size={24} /></span><div><h2>{copy.explore}</h2><p>{selectedState}</p></div></div>
        <div className="pb-explorer-form">
          <label><span>{copy.state}</span><select value={selectedState} onChange={(event) => { setSelectedState(event.target.value); setSelectedDistrict(''); setSelectedMarket('') }}>{stateOptions.map((item) => <option value={item.name} key={item.id}>{item.name}</option>)}</select></label>
          <label><span>{copy.district}</span><select value={selectedDistrict} onChange={(event) => { setSelectedDistrict(event.target.value); setSelectedMarket('') }}><option value="">All districts</option>{districtOptions.map((item) => <option value={item.name} key={item.id}>{item.name}</option>)}</select></label>
          <label><span>{copy.market}</span><select value={selectedMarket} onChange={(event) => setSelectedMarket(event.target.value)}><option value="">All markets</option>{directory.map((item) => <option value={item.name} key={item.id}>{item.name}</option>)}</select></label>
          <label><span>{copy.variety}</span><select value={selectedVariety} onChange={(event) => setSelectedVariety(event.target.value)}><option value="">All varieties</option>{filters.varieties.map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
          <button type="button" onClick={applyLocation}><SlidersHorizontal size={18} />{copy.fetch}</button>
        </div>
      </section>

      <section className="pb-mandi-gallery">
        <div className="pb-section-title-line"><div><h2>{copy.directory}</h2><p>{directory.length} listed markets</p></div><label><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search markets" /></label></div>
        <div className="pb-mandi-gallery-grid">
          {directory.map((item, index) => (
            <button type="button" key={item.id} onClick={() => chooseLocation(item.state, item.district, item.name)}>
              <span className={`pb-mandi-orb tone-${tileTones[index % tileTones.length]}`}><MapPin size={28} strokeWidth={1.7} /></span>
              <strong>{item.name}</strong>
              <small>{item.district}, {item.state}</small>
            </button>
          ))}
        </div>
      </section>

      <section className="pb-market-records">
        <div className="pb-records-heading"><div><h2>{copy.records}</h2><p>{visiblePrices.length} rows</p></div></div>
        {visiblePrices.length ? (
          <div className="pb-market-table-wrap"><table><thead><tr><th>Market</th><th>District</th><th>Variety</th><th>Date</th><th>Min</th><th>Modal</th><th>Max</th><th>{copy.source}</th></tr></thead><tbody>{visiblePrices.map((price) => <tr key={`${price.market}-${price.variety}-${price.arrival_date}`}><td><strong>{price.market}</strong></td><td>{price.district}</td><td><strong>{price.variety}</strong><small>{price.grade}</small></td><td>{formatDate(price.arrival_date, language)}</td><td>{formatCurrency(price.min_price, 0, language)}</td><td><strong className="pb-modal-price">{formatCurrency(price.modal_price, 0, language)}</strong></td><td>{formatCurrency(price.max_price, 0, language)}</td><td>{price.source}</td></tr>)}</tbody></table></div>
        ) : <div className="pb-market-empty"><AlertCircle size={24} /><strong>{copy.empty}</strong></div>}
      </section>

      <section className="pb-market-note">
        <AlertCircle size={19} />
        <div>
          <strong>{copy.analytics}</strong>
          <p>{analytics?.summary.record_count ? `${analytics.summary.record_count} historical records, freshness ${analytics.freshness}.` : 'Historical analytics are not available for the current filters.'}</p>
        </div>
      </section>
    </div>
  )
}
