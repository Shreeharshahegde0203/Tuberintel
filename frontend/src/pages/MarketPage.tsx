import {
  AlertCircle,
  ArrowRight,
  Building2,
  CalendarDays,
  CheckCircle2,
  Database,
  IndianRupee,
  Landmark,
  MapPin,
  PackageOpen,
  RefreshCw,
  Search,
  SlidersHorizontal,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { ErrorState, LoadingState } from '../components/Common'
import { PotatoActionIcon } from '../components/PotatoActionIcon'
import { persistMarketLocation, readMarketLocation, type MarketLocation } from '../data/marketLocations'
import { useI18n } from '../i18n/I18nContext'
import {
  getMandiDirectory,
  getMandiStates,
  getMarketFilters,
  getMarketOverview,
  getMarketPrices,
  refreshMarket,
  syncMandiDirectory,
} from '../services/api'
import { formatCurrency, formatDate } from '../services/format'
import type {
  MandiDirectoryItem,
  MandiDirectoryResponse,
  MarketFilters,
  MarketOverview,
  MarketPrice,
  MarketStateOption,
} from '../types'

const tileTones = ['teal', 'amber', 'blue', 'violet', 'rose', 'cyan', 'orange', 'indigo'] as const

type Selection = {
  state: string
  district: string
  market: string
  variety: string
}

export default function MarketPage() {
  const initialLocation = readMarketLocation()
  const [selection, setSelection] = useState<Selection>({
    state: initialLocation.state,
    district: initialLocation.district,
    market: initialLocation.market,
    variety: '',
  })
  const [applied, setApplied] = useState<Selection>({
    state: initialLocation.state,
    district: initialLocation.district,
    market: initialLocation.market,
    variety: '',
  })
  const [stateOptions, setStateOptions] = useState<MarketStateOption[]>([])
  const [directory, setDirectory] = useState<MandiDirectoryResponse | null>(null)
  const [overview, setOverview] = useState<MarketOverview | null>(null)
  const [filters, setFilters] = useState<MarketFilters | null>(null)
  const [prices, setPrices] = useState<MarketPrice[]>([])
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [directoryLoading, setDirectoryLoading] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [fatalError, setFatalError] = useState('')
  const [directoryMessage, setDirectoryMessage] = useState('')
  const [message, setMessage] = useState('')
  const { language, t } = useI18n()

  const copy = language === 'kn'
    ? {
        title: 'ಮಂಡಿ ಬೆಲೆಗಳು', subtitle: 'ಅಧಿಕೃತ ಕೃಷಿ ಮಾರುಕಟ್ಟೆ ದರಗಳು ಮತ್ತು APMC ಡೈರೆಕ್ಟರಿ.',
        report: 'ಏಕೀಕೃತ ಮಂಡಿ ವರದಿ', reportText: 'ಎಲ್ಲ ಮಂಡಿಗಳು • ಒಂದು ನೋಟ • ಒಂದು ಸರಾಸರಿ ಬೆಲೆ',
        date: 'ದಿನಾಂಕ', active: 'ಸಕ್ರಿಯ ಮಂಡಿಗಳು', records: 'ಬೆಲೆ ದಾಖಲೆಗಳು', average: 'ಸರಾಸರಿ ಮಾದರಿ ಬೆಲೆ',
        range: 'ಕನಿಷ್ಠ–ಗರಿಷ್ಠ', popular: 'ಪ್ರಮುಖ ಮಂಡಿಗಳು', popularText: 'ಇತ್ತೀಚಿನ ಆಲೂಗಡ್ಡೆ ದರಗಳ ಆಧಾರದ ಮೇಲೆ', live: 'ಲೈವ್',
        explore: 'ರಾಜ್ಯ, ಜಿಲ್ಲೆ ಮತ್ತು APMC ಆಯ್ಕೆ ಮಾಡಿ', exploreText: 'ರಾಜ್ಯ ಪಟ್ಟಿ ಡೇಟಾಬೇಸ್‌ನಿಂದ ಬರುತ್ತದೆ; APMC ಪಟ್ಟಿ ಅಧಿಕೃತ ಫೀಡ್‌ನಿಂದ ಸಿಂಕ್ ಆಗುತ್ತದೆ.',
        state: 'ರಾಜ್ಯ', district: 'ಜಿಲ್ಲೆ', mandi: 'APMC / ಮಂಡಿ', variety: 'ತಳಿ', allDistricts: 'ಎಲ್ಲ ಜಿಲ್ಲೆಗಳು', allMandis: 'ಎಲ್ಲ ಮಂಡಿಗಳು', allVarieties: 'ಎಲ್ಲ ತಳಿಗಳು',
        fetch: 'ಮಂಡಿ ಬೆಲೆ ಪಡೆಯಿರಿ', refresh: 'ಬೆಲೆ ಡೇಟಾ ನವೀಕರಿಸಿ', sync: 'ಅಧಿಕೃತ APMC ಪಟ್ಟಿ ಸಿಂಕ್ ಮಾಡಿ', syncing: 'ಸಿಂಕ್ ಆಗುತ್ತಿದೆ…',
        table: 'ಮಂಡಿ-ವಾರು ಬೆಲೆ ವಿವರ', search: 'ಮಂಡಿ ಅಥವಾ ತಳಿ ಹುಡುಕಿ…', market: 'ಮಂಡಿ', arrival: 'ದಿನಾಂಕ', min: 'ಕನಿಷ್ಠ', modal: 'ಮಾದರಿ', max: 'ಗರಿಷ್ಠ', source: 'ಮೂಲ', noRecords: 'ಈ ಆಯ್ಕೆಗೆ ಬೆಲೆ ದಾಖಲೆಗಳು ಲಭ್ಯವಿಲ್ಲ.',
        directoryReady: 'APMC ಡೈರೆಕ್ಟರಿ ಸಿದ್ಧವಾಗಿದೆ', directoryEmpty: 'ಈ ರಾಜ್ಯದ APMC ಪಟ್ಟಿ ಇನ್ನೂ ಸಿಂಕ್ ಆಗಿಲ್ಲ', directoryCount: 'ಡೇಟಾಬೇಸ್ ಮಂಡಿಗಳು', apiMissing: 'DATA_GOV_API_KEY ಬ್ಯಾಕೆಂಡ್‌ನಲ್ಲಿ ಅಗತ್ಯವಿದೆ.',
        sourceLabel: 'ಅಧಿಕೃತ ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ', updated: 'ನವೀಕರಿಸಲಾಗಿದೆ', chooseState: 'ರಾಜ್ಯ ಆಯ್ಕೆ ಮಾಡಿ', chooseDistrict: 'ಜಿಲ್ಲೆ ಆಯ್ಕೆ ಮಾಡಿ', chooseMandi: 'APMC / ಮಂಡಿ ಆಯ್ಕೆ ಮಾಡಿ',
      }
    : {
        title: 'Mandi Prices', subtitle: 'Official agricultural market rates with a database-backed APMC directory.',
        report: 'Consolidated Mandi Report', reportText: 'All mandis • One view • One average price',
        date: 'Date', active: 'Active mandis', records: 'Price records', average: 'Average modal price',
        range: 'Minimum–maximum', popular: 'Top mandis', popularText: 'Based on the latest available potato observations', live: 'LIVE',
        explore: 'Choose state, district and APMC', exploreText: 'States come from the reference database; APMCs are synchronised from the official market feed.',
        state: 'State', district: 'District', mandi: 'APMC / mandi', variety: 'Variety', allDistricts: 'All districts', allMandis: 'All APMCs / mandis', allVarieties: 'All varieties',
        fetch: 'Fetch Mandi Price', refresh: 'Refresh price data', sync: 'Sync official APMC directory', syncing: 'Synchronising…',
        table: 'Market-wise price details', search: 'Search mandi or variety…', market: 'Mandi', arrival: 'Date', min: 'Min', modal: 'Modal', max: 'Max', source: 'Source', noRecords: 'No price records are available for this selection.',
        directoryReady: 'APMC directory ready', directoryEmpty: 'The APMC directory for this state has not been synchronised', directoryCount: 'mandis in database', apiMissing: 'Add DATA_GOV_API_KEY in the backend to synchronise it.',
        sourceLabel: 'Official market intelligence', updated: 'Updated', chooseState: 'Choose state', chooseDistrict: 'Choose district', chooseMandi: 'Choose APMC / mandi',
      }

  const loadDirectory = async (stateName: string, preferred?: Partial<Selection>) => {
    setDirectoryLoading(true)
    setDirectoryMessage('')
    try {
      const data = await getMandiDirectory(stateName)
      setDirectory(data)
      const districts = data.districts || []
      const district = preferred?.district && districts.includes(preferred.district) ? preferred.district : ''
      const possible = data.mandis.filter((item) => !district || item.district === district)
      const market = preferred?.market && possible.some((item) => item.market === preferred.market) ? preferred.market : ''
      setSelection((current) => ({ ...current, state: data.state || stateName, district, market }))
      if (!data.count) setDirectoryMessage(data.api_configured ? copy.directoryEmpty : `${copy.directoryEmpty}. ${copy.apiMissing}`)
    } catch (error: any) {
      setDirectory(null)
      setDirectoryMessage(error?.response?.data?.detail || error.message || copy.directoryEmpty)
    } finally {
      setDirectoryLoading(false)
    }
  }

  const loadMarket = async (next: Selection) => {
    setLoading(true)
    setFatalError('')
    try {
      const [overviewData, filterData, priceData] = await Promise.all([
        getMarketOverview(next.state),
        getMarketFilters(next.state),
        getMarketPrices({
          state: next.state,
          district: next.district || undefined,
          market: next.market || undefined,
          variety: next.variety || undefined,
          latest_only: true,
          limit: 1000,
        }),
      ])
      setOverview(overviewData)
      setFilters(filterData)
      setPrices(priceData)
    } catch (error: any) {
      setFatalError(error?.response?.data?.detail || error.message || 'Unable to load mandi data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    void Promise.all([getMandiStates(), getMandiDirectory(initialLocation.state)])
      .then(([states, mandiDirectory]) => {
        if (!active) return
        setStateOptions(states)
        setDirectory(mandiDirectory)
        const districtValid = mandiDirectory.districts.includes(initialLocation.district)
        const marketValid = mandiDirectory.mandis.some((item) => item.market === initialLocation.market)
        const firstSelection = {
          state: initialLocation.state,
          district: districtValid ? initialLocation.district : '',
          market: marketValid ? initialLocation.market : '',
          variety: '',
        }
        setSelection(firstSelection)
        setApplied(firstSelection)
        void loadMarket(firstSelection)
      })
      .catch((error: any) => {
        if (active) setFatalError(error?.response?.data?.detail || error.message || 'Unable to initialise market data')
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    const listener = (event: Event) => {
      const location = (event as CustomEvent<MarketLocation>).detail
      const next = { state: location.state, district: location.district, market: location.market, variety: '' }
      setSelection(next)
      setApplied(next)
      void loadDirectory(location.state, next)
      void loadMarket(next)
    }
    window.addEventListener('tuberintel-location', listener)
    return () => window.removeEventListener('tuberintel-location', listener)
  }, [])

  const districtOptions = directory?.districts || []
  const mandiOptions = useMemo(
    () => (directory?.mandis || []).filter((item) => !selection.district || item.district === selection.district),
    [directory?.mandis, selection.district],
  )

  const onStateChange = (stateName: string) => {
    setSelection({ state: stateName, district: '', market: '', variety: '' })
    setFilters(null)
    void loadDirectory(stateName)
    void getMarketFilters(stateName).then(setFilters).catch(() => setFilters(null))
  }

  const onDistrictChange = (district: string) => {
    setSelection((current) => ({ ...current, district, market: '' }))
  }

  const applyFilters = () => {
    setApplied(selection)
    const matchingMandi = (directory?.mandis || []).find((item) => item.market === selection.market)
    persistMarketLocation({
      state: selection.state,
      district: selection.district || matchingMandi?.district || '',
      market: selection.market || '',
    })
    void loadMarket(selection)
  }

  const runDirectorySync = async () => {
    setSyncing(true)
    setDirectoryMessage('')
    try {
      const result = await syncMandiDirectory(selection.state)
      setDirectoryMessage(result.note)
      await loadDirectory(selection.state)
    } catch (error: any) {
      setDirectoryMessage(error?.response?.data?.detail || error.message || 'Directory synchronisation failed')
    } finally {
      setSyncing(false)
    }
  }

  const runPriceRefresh = async () => {
    setRefreshing(true)
    setMessage('')
    try {
      const result = await refreshMarket(applied.state, applied.district || undefined)
      setMessage(`${result.note} ${result.received} ${t('market.recordsReceived')}, ${result.inserted} ${t('market.newRecords')}.`)
      await loadMarket(applied)
      await loadDirectory(applied.state, applied)
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || error.message || 'Price refresh failed')
    } finally {
      setRefreshing(false)
    }
  }

  const visiblePrices = useMemo(() => {
    const term = query.trim().toLowerCase()
    if (!term) return prices
    return prices.filter((row) => `${row.market} ${row.district} ${row.variety} ${row.grade}`.toLowerCase().includes(term))
  }, [prices, query])

  if (fatalError) return <ErrorState message={String(fatalError)} retry={() => void loadMarket(applied)} />
  if (loading && !overview) return <LoadingState />
  if (!overview) return <LoadingState />

  const report = overview.consolidated
  const DirectionIcon = report.direction === 'falling' ? TrendingDown : TrendingUp
  const topMandis = overview.top_markets.slice(0, 10)
  const directoryLive = Boolean(directory?.count)
  const directorySource = directory?.source || 'database'

  const selectMandi = (item: MandiDirectoryItem) => {
    const next = { state: item.state, district: item.district, market: item.market, variety: '' }
    setSelection(next)
    setApplied(next)
    persistMarketLocation({ state: item.state, district: item.district, market: item.market })
    void loadMarket(next)
  }

  return (
    <div className="pb-market-page">
      <section className="pb-market-title-row">
        <div><span className="pb-market-kicker"><Landmark size={16} />{copy.sourceLabel}</span><h1>{copy.title}</h1><p>{copy.subtitle}</p></div>
        <div className={`pb-live-source ${overview.live_data ? 'live' : 'demo'}`}><span /><div><strong>{overview.live_data ? 'AGMARKNET / data.gov.in' : 'Demonstration prices'}</strong><small>{copy.updated}: {overview.freshness}</small></div><Database size={19} /></div>
      </section>

      {message && <div className="pb-market-message"><CheckCircle2 size={18} /><span>{message}</span></div>}

      <section className="pb-market-overview-layout">
        <article className="pb-consolidated-report">
          <div className="pb-report-heading"><div><span>{copy.report}</span><h2>{copy.reportText}</h2><p>{applied.state}{applied.district ? ` · ${applied.district}` : ''}{applied.market ? ` · ${applied.market}` : ''}</p></div><span className="pb-new-pill">POTATO</span></div>
          <div className="pb-report-metrics">
            <div><span className="pb-metric-icon mint"><CalendarDays size={20} /></span><small>{copy.date}</small><strong>{report.date ? formatDate(report.date, language) : '—'}</strong></div>
            <div><span className="pb-metric-icon blue"><Building2 size={20} /></span><small>{copy.active}</small><strong>{report.active_mandis}</strong></div>
            <div><span className="pb-metric-icon amber"><PackageOpen size={20} /></span><small>{copy.records}</small><strong>{report.records}</strong></div>
            <div><span className="pb-metric-icon green"><IndianRupee size={20} /></span><small>{copy.average}</small><strong>{formatCurrency(report.average_modal_price, 0, language)}</strong></div>
          </div>
          <div className="pb-report-footer">
            <div><span>{copy.range}</span><strong>{formatCurrency(report.minimum_price, 0, language)} – {formatCurrency(report.maximum_price, 0, language)}</strong></div>
            <div className={report.change_percent_7d < 0 ? 'negative' : 'positive'}><DirectionIcon size={18} /><span>7D</span><strong>{report.change_percent_7d >= 0 ? '+' : ''}{report.change_percent_7d.toFixed(1)}%</strong></div>
            <button type="button" onClick={runPriceRefresh} disabled={refreshing}><RefreshCw className={refreshing ? 'spin' : ''} size={17} />{refreshing ? copy.syncing : copy.refresh}</button>
          </div>
        </article>

        <aside className="pb-popular-rail">
          <div className="pb-popular-rail-heading"><div><span>{copy.popular}</span><small>{copy.popularText}</small></div><em>{copy.live}</em></div>
          <div className="pb-popular-rail-list">
            {topMandis.slice(0, 6).map((item, index) => (
              <button type="button" key={`${item.market}-${item.variety}`} onClick={() => selectMandi({ id: index, state: item.state, district: item.district, market: item.market, source: 'price history', is_enam: null, last_seen_at: item.arrival_date })}>
                <PotatoActionIcon icon={Landmark} tone={tileTones[index % tileTones.length]} size="sm" />
                <span><strong>{item.market}</strong><small>{item.district}</small></span><ArrowRight size={16} />
              </button>
            ))}
            {!topMandis.length && <div className="pb-market-empty compact"><AlertCircle size={22} /><strong>{copy.noRecords}</strong></div>}
          </div>
        </aside>
      </section>

      <section className="pb-market-explorer">
        <div className="pb-explorer-heading"><PotatoActionIcon icon={Search} tone="teal" size="lg" /><div><h2>{copy.explore}</h2><p>{copy.exploreText}</p></div></div>

        <div className={`pb-market-directory-status ${syncing ? 'syncing' : directoryLive ? 'live' : ''}`}>
          <span />
          <div><strong>{directoryLive ? copy.directoryReady : copy.directoryEmpty}</strong><small>{directory?.count || 0} {copy.directoryCount} · {directorySource}</small></div>
          <button type="button" onClick={runDirectorySync} disabled={syncing || !directory?.api_configured}><RefreshCw className={syncing ? 'spin' : ''} size={15} />{syncing ? copy.syncing : copy.sync}</button>
        </div>

        {directoryMessage && <div className="pb-market-warning"><AlertCircle size={18} /><span>{directoryMessage}</span></div>}

        <div className="pb-explorer-form mandi-directory-form">
          <label><span>{copy.state}</span><select value={selection.state} onChange={(event) => onStateChange(event.target.value)} disabled={directoryLoading}><option value="">{copy.chooseState}</option>{stateOptions.map((item) => <option value={item.name} key={item.code}>{item.name}{item.mandi_count ? ` (${item.mandi_count})` : ''}</option>)}</select></label>
          <label><span>{copy.district}</span><select value={selection.district} onChange={(event) => onDistrictChange(event.target.value)} disabled={directoryLoading || !districtOptions.length}><option value="">{districtOptions.length ? copy.allDistricts : copy.chooseDistrict}</option>{districtOptions.map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
          <label><span>{copy.mandi}</span><select value={selection.market} onChange={(event) => setSelection((current) => ({ ...current, market: event.target.value }))} disabled={directoryLoading || !mandiOptions.length}><option value="">{mandiOptions.length ? copy.allMandis : copy.chooseMandi}</option>{mandiOptions.map((item) => <option value={item.market} key={`${item.district}-${item.market}`}>{item.market}{selection.district ? '' : ` — ${item.district}`}</option>)}</select></label>
          <label><span>{copy.variety}</span><select value={selection.variety} onChange={(event) => setSelection((current) => ({ ...current, variety: event.target.value }))}><option value="">{copy.allVarieties}</option>{(filters?.varieties || []).map((item) => <option value={item} key={item}>{item}</option>)}</select></label>
          <button type="button" onClick={applyFilters} disabled={!selection.state}><SlidersHorizontal size={18} />{copy.fetch}</button>
        </div>
        <div className="pb-select-help"><span>{selection.district || copy.allDistricts} · {selection.market || copy.allMandis}</span><strong>{mandiOptions.length} APMC / mandi options</strong></div>

        {!!mandiOptions.length && (
          <div className="pb-mandi-directory-list">
            {mandiOptions.slice(0, 6).map((item, index) => <button className="pb-mandi-directory-chip" type="button" key={`${item.district}-${item.market}`} onClick={() => selectMandi(item)}><PotatoActionIcon icon={Landmark} tone={tileTones[index % tileTones.length]} size="sm" /><span><strong>{item.market}</strong><small>{item.district} · {item.source}</small></span><ArrowRight size={15} /></button>)}
          </div>
        )}
      </section>

      <section className="pb-mandi-gallery">
        <div className="pb-section-title-line"><div><h2>{copy.popular}</h2><p>{copy.popularText}</p></div><span>{applied.state}</span></div>
        <div className="pb-mandi-gallery-grid">
          {topMandis.map((item, index) => (
            <button type="button" key={`${item.market}-${item.rank}`} onClick={() => {
              const next = { state: item.state, district: item.district, market: item.market, variety: '' }
              setSelection(next); setApplied(next); void loadMarket(next)
            }}>
              <span className={`pb-mandi-orb tone-${tileTones[index % tileTones.length]}`}><Landmark size={28} strokeWidth={1.7} /><em>{item.rank}</em></span>
              <strong>{item.market}</strong><small>{formatCurrency(item.modal_price, 0, language)} / qtl</small>
            </button>
          ))}
        </div>
      </section>

      <section className="pb-market-records">
        <div className="pb-records-heading"><div><h2>{copy.table}</h2><p>{visiblePrices.length} {copy.records.toLowerCase()}</p></div><label><Search size={18} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={copy.search} /></label></div>
        <div className="pb-market-table-wrap"><table><thead><tr><th>{copy.market}</th><th>{copy.district}</th><th>{copy.variety}</th><th>{copy.arrival}</th><th>{copy.min}</th><th>{copy.modal}</th><th>{copy.max}</th><th>{copy.source}</th></tr></thead><tbody>{visiblePrices.map((price) => <tr key={`${price.market}-${price.variety}-${price.arrival_date}`}><td><strong>{price.market}</strong></td><td><MapPin size={14} />{price.district}</td><td><strong>{price.variety}</strong><small>{price.grade}</small></td><td>{formatDate(price.arrival_date, language)}</td><td>{formatCurrency(price.min_price, 0, language)}</td><td><strong className="pb-modal-price">{formatCurrency(price.modal_price, 0, language)}</strong></td><td>{formatCurrency(price.max_price, 0, language)}</td><td><span className={price.source.toLowerCase().includes('data.gov.in') ? 'pb-source-badge live' : 'pb-source-badge demo'}>{price.source.toLowerCase().includes('data.gov.in') ? 'AGMARKNET' : 'DEMO'}</span></td></tr>)}</tbody></table></div>
        {!visiblePrices.length && <div className="pb-market-empty"><AlertCircle size={24} /><strong>{copy.noRecords}</strong></div>}
      </section>

      <div className="pb-market-note"><AlertCircle size={19} /><div><strong>{t('market.arrivalUnavailable')}</strong><p>{report.arrival_volume_note}</p></div></div>
    </div>
  )
}
