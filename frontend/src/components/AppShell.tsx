import {
  BarChart3,
  Boxes,
  Check,
  ChevronDown,
  ClipboardList,
  Database,
  Languages,
  Landmark,
  LogOut,
  Menu,
  Newspaper,
  PackageCheck,
  Search,
  Settings,
  Store,
  UserRound,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { FarmerAssistant } from './FarmerAssistant'
import { useI18n } from '../i18n/I18nContext'
import { persistMarketLocation, readMarketLocation, type MarketLocation } from '../data/marketLocations'
import { getMandiDirectory, getMandiStates } from '../services/api'
import type { MandiDirectoryItem, MarketStateOption } from '../types'

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [locationOpen, setLocationOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState<MarketLocation>(() => readMarketLocation())
  const [draftLocation, setDraftLocation] = useState<MarketLocation>(() => readMarketLocation())
  const [stateOptions, setStateOptions] = useState<MarketStateOption[]>([])
  const [directoryMandis, setDirectoryMandis] = useState<MandiDirectoryItem[]>([])
  const [locationLoading, setLocationLoading] = useState(false)
  const [locationMessage, setLocationMessage] = useState('')
  const locationWrapRef = useRef<HTMLDivElement>(null)
  const profileWrapRef = useRef<HTMLDivElement>(null)
  const { user, signOut } = useAuth()
  const { language, setLanguage } = useI18n()
  const navigate = useNavigate()

  const copy = language === 'kn'
    ? {
        overview: 'ಅವಲೋಕನ', inspect: 'ಗುಣಮಟ್ಟ ಪರಿಶೀಲನೆ', market: 'ಮಂಡಿ ಬೆಲೆ', history: 'ಬ್ಯಾಚ್‌ಗಳು',
        models: 'ಮಾದರಿಗಳು ಮತ್ತು ವಿಧಾನಗಳು', trade: 'ಖರೀದಿ / ಮಾರಾಟ', analytics: 'ಬೆಲೆ ವಿಶ್ಲೇಷಣೆ', news: 'ಮಾರುಕಟ್ಟೆ ಮಾಹಿತಿ',
        search: 'ಮಂಡಿ, ತಳಿ ಅಥವಾ ಸುದ್ದಿ ಹುಡುಕಿ…', location: 'ಆಯ್ದ ಮಾರುಕಟ್ಟೆ', account: 'ನನ್ನ ಖಾತೆ', signOut: 'ಸೈನ್ ಔಟ್',
        state: 'ರಾಜ್ಯ', district: 'ಜಿಲ್ಲೆ', mandi: 'APMC / ಮಂಡಿ', apply: 'ಮಾರುಕಟ್ಟೆ ಆಯ್ಕೆಮಾಡಿ',
        noMandis: 'ಈ ರಾಜ್ಯದ ಅಧಿಕೃತ ಮಂಡಿ ಡೈರೆಕ್ಟರಿಯನ್ನು ಇನ್ನೂ ಸಿಂಕ್ ಮಾಡಿಲ್ಲ.', primary: 'ಕಾರ್ಯಸ್ಥಳ', intelligence: 'ಮಾಹಿತಿ', technical: 'ತಾಂತ್ರಿಕ',
      }
    : {
        overview: 'Overview', inspect: 'Quality check', market: 'Mandi prices', history: 'Batches',
        models: 'Models & methods', trade: 'Buy / Sell', analytics: 'Price analytics', news: 'Market intelligence',
        search: 'Search mandi, variety or news…', location: 'Selected market', account: 'My account', signOut: 'Sign out',
        state: 'State', district: 'District', mandi: 'APMC / mandi', apply: 'Use this market',
        noMandis: 'The official reporting-mandi directory for this state has not been synced yet.', primary: 'Workspace', intelligence: 'Intelligence', technical: 'Technical',
      }

  const primaryNav = useMemo(() => [
    { to: '/', label: copy.overview, icon: Store },
    { to: '/market', label: copy.market, icon: Landmark },
    { to: '/analyze', label: copy.inspect, icon: PackageCheck },
    { to: '/history', label: copy.history, icon: ClipboardList },
    { to: '/trade', label: copy.trade, icon: Boxes },
  ], [copy.overview, copy.market, copy.inspect, copy.history, copy.trade])

  const intelligenceNav = useMemo(() => [
    { to: '/analytics', label: copy.analytics, icon: BarChart3 },
    { to: '/news', label: copy.news, icon: Newspaper },
  ], [copy.analytics, copy.news])

  const districtOptions = useMemo(
    () => Array.from(new Set(directoryMandis.map((item) => item.district))).sort((a, b) => a.localeCompare(b)),
    [directoryMandis],
  )
  const mandiOptions = useMemo(
    () => directoryMandis.filter((item) => !draftLocation.district || item.district === draftLocation.district),
    [directoryMandis, draftLocation.district],
  )

  const loadDirectory = async (state: string, preferred?: MarketLocation) => {
    setLocationLoading(true)
    setLocationMessage('')
    try {
      const data = await getMandiDirectory(state)
      setDirectoryMandis(data.mandis || [])
      const districts = Array.from(new Set((data.mandis || []).map((item) => item.district))).sort((a, b) => a.localeCompare(b))
      const district = preferred?.district && districts.includes(preferred.district) ? preferred.district : districts[0] || ''
      const possibleMandis = (data.mandis || []).filter((item) => !district || item.district === district)
      const market = preferred?.market && possibleMandis.some((item) => item.market === preferred.market)
        ? preferred.market
        : possibleMandis[0]?.market || ''
      setDraftLocation({ state: data.state || state, district, market })
      if (!data.mandis?.length) setLocationMessage(copy.noMandis)
    } catch (error: any) {
      setDirectoryMandis([])
      setLocationMessage(error?.response?.data?.detail || error.message || copy.noMandis)
      setDraftLocation({ state, district: '', market: '' })
    } finally {
      setLocationLoading(false)
    }
  }

  useEffect(() => {
    let active = true
    void getMandiStates()
      .then((items) => { if (active) setStateOptions(items || []) })
      .catch(() => { if (active) setStateOptions([]) })
    return () => { active = false }
  }, [])

  useEffect(() => {
    void loadDirectory(location.state, location)
    // The selected market is intentionally loaded once here; subsequent loads are user-driven.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const closeMenus = (event: MouseEvent) => {
      const target = event.target as Node
      if (locationWrapRef.current && !locationWrapRef.current.contains(target)) setLocationOpen(false)
      if (profileWrapRef.current && !profileWrapRef.current.contains(target)) setProfileOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { setLocationOpen(false); setProfileOpen(false); setMobileOpen(false) }
    }
    document.addEventListener('mousedown', closeMenus)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeMenus)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    const value = query.trim()
    if (!value) return
    navigate(`/market?search=${encodeURIComponent(value)}`)
    setQuery('')
  }

  const changeDraftState = (state: string) => {
    setDraftLocation({ state, district: '', market: '' })
    void loadDirectory(state)
  }

  const changeDraftDistrict = (district: string) => {
    const firstMarket = directoryMandis.find((item) => item.district === district)?.market || ''
    setDraftLocation((current) => ({ ...current, district, market: firstMarket }))
  }

  const applyLocation = () => {
    setLocation(draftLocation)
    persistMarketLocation(draftLocation)
    setLocationOpen(false)
  }

  const openLocation = () => {
    setDraftLocation(location)
    if (!locationOpen) void loadDirectory(location.state, location)
    setLocationOpen((value) => !value)
    setProfileOpen(false)
  }

  const navBlock = (items: typeof primaryNav, closeMobile = false) => items.map(({ to, label, icon: Icon }) => (
    <NavLink key={to} to={to} end={to === '/'} onClick={closeMobile ? () => setMobileOpen(false) : undefined}>
      <Icon size={18} />
      <span>{label}</span>
    </NavLink>
  ))

  return (
    <div className="ops-app-shell">
      <aside className={`ops-sidebar ${mobileOpen ? 'open' : ''}`} aria-label="Application navigation">
        <div className="ops-sidebar-head">
          <NavLink to="/" className="ops-brand" aria-label="TuberIntel home" onClick={() => setMobileOpen(false)}>
            <img src="/brand/tuber-mitra.png" alt="" />
            <span><strong>TuberIntel</strong><small>Potato operations</small></span>
          </NavLink>
          <button className="ops-sidebar-close" type="button" onClick={() => setMobileOpen(false)} aria-label="Close navigation"><X size={20} /></button>
        </div>

        <div className="ops-nav-section">
          <span className="ops-nav-label">{copy.primary}</span>
          <nav className="ops-nav">{navBlock(primaryNav, true)}</nav>
        </div>

        <div className="ops-nav-section">
          <span className="ops-nav-label">{copy.intelligence}</span>
          <nav className="ops-nav">{navBlock(intelligenceNav, true)}</nav>
        </div>

        <div className="ops-sidebar-spacer" />

        <div className="ops-nav-section ops-nav-secondary">
          <span className="ops-nav-label">{copy.technical}</span>
          <nav className="ops-nav">
            <NavLink to="/models" onClick={() => setMobileOpen(false)}><Database size={18} /><span>{copy.models}</span></NavLink>
          </nav>
        </div>

        <div className="ops-sidebar-profile">
          <span className="ops-user-avatar"><UserRound size={18} /></span>
          <div><strong>{user?.name || 'TuberIntel user'}</strong><small>{user?.email || copy.account}</small></div>
        </div>
      </aside>

      {mobileOpen && <button className="ops-sidebar-backdrop" type="button" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}

      <div className="ops-workspace">
        <header className="ops-topbar">
          <button className="ops-mobile-menu" type="button" onClick={() => setMobileOpen(true)} aria-label="Open navigation"><Menu size={21} /></button>

          <div className="ops-location-wrap" ref={locationWrapRef}>
            <button className="ops-location-button" type="button" onClick={openLocation} aria-expanded={locationOpen}>
              <Landmark size={17} />
              <span><small>{copy.location}</small><strong>{location.market || location.district || location.state}</strong></span>
              <em>{location.district ? `${location.district}, ${location.state}` : location.state}</em>
              <ChevronDown size={15} />
            </button>
            {locationOpen && (
              <div className="ops-location-popover">
                <div className="ops-popover-title"><Landmark size={18} /><div><strong>{copy.location}</strong><small>{draftLocation.market || draftLocation.district || draftLocation.state}</small></div></div>
                <label><span>{copy.state}</span><select value={draftLocation.state} onChange={(event) => changeDraftState(event.target.value)} disabled={locationLoading}>{stateOptions.map((item) => <option value={item.name} key={item.code}>{item.name}{item.mandi_count ? ` (${item.mandi_count})` : ''}</option>)}</select></label>
                <label><span>{copy.district}</span><select value={draftLocation.district} onChange={(event) => changeDraftDistrict(event.target.value)} disabled={locationLoading || !districtOptions.length}><option value="">{locationLoading ? 'Loading…' : 'Select district'}</option>{districtOptions.map((district) => <option value={district} key={district}>{district}</option>)}</select></label>
                <label><span>{copy.mandi}</span><select value={draftLocation.market} onChange={(event) => setDraftLocation((current) => ({ ...current, market: event.target.value }))} disabled={locationLoading || !mandiOptions.length}><option value="">{locationLoading ? 'Loading…' : 'Select APMC / mandi'}</option>{mandiOptions.map((item) => <option value={item.market} key={`${item.district}-${item.market}`}>{item.market}</option>)}</select></label>
                {locationMessage && <p className="ops-location-message">{locationMessage}</p>}
                <button className="ops-location-apply" type="button" onClick={applyLocation} disabled={!draftLocation.state}><Check size={16} />{copy.apply}</button>
              </div>
            )}
          </div>

          <form className="ops-global-search" onSubmit={submitSearch}>
            <Search size={17} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={copy.search} aria-label={copy.search} />
          </form>

          <div className="ops-topbar-actions">
            <button className="ops-language-button" type="button" onClick={() => setLanguage(language === 'en' ? 'kn' : 'en')}><Languages size={17} /><span>{language === 'en' ? 'ಕನ್ನಡ' : 'English'}</span></button>
            <div className="ops-profile-wrap" ref={profileWrapRef}>
              <button className="ops-profile-button" type="button" onClick={() => { setProfileOpen((value) => !value); setLocationOpen(false) }} aria-expanded={profileOpen}>
                {user?.avatarUrl ? <img src={user.avatarUrl} alt="" /> : <span><UserRound size={18} /></span>}
                <strong>{user?.name || 'Farmer'}</strong>
                <ChevronDown size={15} />
              </button>
              {profileOpen && (
                <div className="ops-profile-popover">
                  <div className="ops-profile-summary"><span><UserRound size={19} /></span><div><strong>{user?.name || 'TuberIntel user'}</strong><small>{user?.email || copy.account}</small></div></div>
                  <NavLink to="/models" onClick={() => setProfileOpen(false)}><Settings size={16} />{copy.models}</NavLink>
                  <button className="danger" type="button" onClick={() => void signOut()}><LogOut size={16} />{copy.signOut}</button>
                </div>
              )}
            </div>
          </div>
        </header>

        <main className="ops-main"><Outlet /></main>
      </div>

      <FarmerAssistant />

      <nav className="ops-mobile-bottom-nav" aria-label="Mobile navigation">
        {primaryNav.slice(0, 5).map(({ to, label, icon: Icon }) => <NavLink key={to} to={to} end={to === '/'}><Icon size={19} /><span>{label === copy.inspect ? (language === 'kn' ? 'ಗುಣಮಟ್ಟ' : 'Quality') : label}</span></NavLink>)}
      </nav>
    </div>
  )
}
