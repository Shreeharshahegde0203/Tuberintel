import {
  BarChart3,
  Bell,
  Boxes,
  ChevronDown,
  ClipboardList,
  Home,
  Landmark,
  Languages,
  LogOut,
  MapPin,
  Menu,
  Newspaper,
  PackageCheck,
  Search,
  Settings,
  Snowflake,
  Truck,
  UserRound,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { persistMarketLocation, readMarketLocation, type MarketLocation } from '../data/marketLocations'
import { useI18n } from '../i18n/I18nContext'
import { getMandiDirectory, getMandiDistricts, getMandiStates } from '../services/api'
import type { MandiDirectoryItem, MarketDistrictOption, MarketStateOption } from '../types'
import '../market-ui-phase1.css'

export function AppShell() {
  const [mobileOpen, setMobileOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [locationOpen, setLocationOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState<MarketLocation>(() => readMarketLocation())
  const [draftLocation, setDraftLocation] = useState<MarketLocation>(() => readMarketLocation())
  const [states, setStates] = useState<MarketStateOption[]>([])
  const [districts, setDistricts] = useState<MarketDistrictOption[]>([])
  const [markets, setMarkets] = useState<MandiDirectoryItem[]>([])
  const [marketSearch, setMarketSearch] = useState('')
  const [loadingLocation, setLoadingLocation] = useState(false)
  const locationWrapRef = useRef<HTMLDivElement | null>(null)
  const profileWrapRef = useRef<HTMLDivElement | null>(null)
  const { user, signOut } = useAuth()
  const { language, setLanguage } = useI18n()
  const navigate = useNavigate()

  const copy = language === 'kn'
    ? {
        overview: 'ಅವಲೋಕನ',
        mandi: 'ಮಂಡಿ ಬೆಲೆಗಳು',
        inspect: 'ಗುಣಮಟ್ಟ ಪರಿಶೀಲನೆ',
        history: 'ಬ್ಯಾಚ್ ಇತಿಹಾಸ',
        models: 'ಮಾದರಿಗಳು ಮತ್ತು ವಿಧಾನಗಳು',
        more: 'ಇನ್ನಷ್ಟು',
        analytics: 'ಬೆಲೆ ವಿಶ್ಲೇಷಣೆ',
        storage: 'ಸಂಗ್ರಹ ನಿರ್ಧಾರ',
        transport: 'ಸಾಗಣೆ ಲೆಕ್ಕ',
        news: 'ಸುದ್ದಿ ಮತ್ತು ಯೋಜನೆಗಳು',
        search: 'ಮಂಡಿ, ತಳಿ, ಸುದ್ದಿ ಹುಡುಕಿ…',
        location: 'ಆಯ್ದ ಮಾರುಕಟ್ಟೆ',
        state: 'ರಾಜ್ಯ',
        district: 'ಜಿಲ್ಲೆ / ನಗರ',
        market: 'ಎಪಿಎಂಸಿ / ಮಂಡಿ',
        apply: 'ಸ್ಥಳ ಅನ್ವಯಿಸಿ',
        account: 'ನನ್ನ ಖಾತೆ',
        signOut: 'ಸೈನ್ ಔಟ್',
        loading: 'ಮಾರುಕಟ್ಟೆ ಪಟ್ಟಿಯನ್ನು ಲೋಡ್ ಮಾಡಲಾಗುತ್ತಿದೆ…',
        empty: 'ಈ ಆಯ್ಕೆಗಾಗಿ ಮಾರುಕಟ್ಟೆಗಳು ಲಭ್ಯವಿಲ್ಲ.',
      }
    : {
        overview: 'Overview',
        mandi: 'Mandi Prices',
        inspect: 'Quality Check',
        history: 'Batch History',
        models: 'Models & Methods',
        more: 'More',
        analytics: 'Price Analytics',
        storage: 'Storage Decision',
        transport: 'Transport Estimate',
        news: 'News & Schemes',
        search: 'Search mandis, varieties, news…',
        location: 'Selected market',
        state: 'State',
        district: 'District / city',
        market: 'APMC / market',
        apply: 'Apply location',
        account: 'My account',
        signOut: 'Sign out',
        loading: 'Loading market directory…',
        empty: 'No markets are available for this selection.',
      }

  const primaryNav = useMemo(
    () => [
      { to: '/', label: copy.overview, icon: Home },
      { to: '/market', label: copy.mandi, icon: Landmark },
      { to: '/analyze', label: copy.inspect, icon: PackageCheck },
      { to: '/history', label: copy.history, icon: ClipboardList },
      { to: '/models', label: copy.models, icon: Boxes },
    ],
    [copy.history, copy.inspect, copy.mandi, copy.models, copy.overview],
  )

  const moreNav = [
    { label: copy.analytics, icon: BarChart3 },
    { label: copy.storage, icon: Snowflake },
    { label: copy.transport, icon: Truck },
    { label: copy.news, icon: Newspaper },
  ]

  useEffect(() => {
    const closeMenus = (event: MouseEvent) => {
      const target = event.target as Node
      if (locationWrapRef.current && !locationWrapRef.current.contains(target)) setLocationOpen(false)
      if (profileWrapRef.current && !profileWrapRef.current.contains(target)) setProfileOpen(false)
    }
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setLocationOpen(false)
        setProfileOpen(false)
        setMobileOpen(false)
      }
    }
    document.addEventListener('mousedown', closeMenus)
    document.addEventListener('keydown', closeOnEscape)
    return () => {
      document.removeEventListener('mousedown', closeMenus)
      document.removeEventListener('keydown', closeOnEscape)
    }
  }, [])

  useEffect(() => {
    void getMandiStates().then(setStates).catch(() => setStates([]))
  }, [])

  useEffect(() => {
    if (!draftLocation.state) return
    setLoadingLocation(true)
    void Promise.all([
      getMandiDistricts(draftLocation.state).catch(() => [] as MarketDistrictOption[]),
      getMandiDirectory(draftLocation.state, draftLocation.city || undefined, marketSearch || undefined, 30, 0).catch(
        () =>
          ({
            state: draftLocation.state,
            district: draftLocation.city || null,
            total: 0,
            limit: 30,
            offset: 0,
            items: [],
            source: 'Unavailable',
            live_data: false,
            note: null,
          }),
      ),
    ])
      .then(([districtResult, marketResult]) => {
        setDistricts(districtResult)
        setMarkets(marketResult.items)
      })
      .finally(() => setLoadingLocation(false))
  }, [draftLocation.state, draftLocation.city, marketSearch])

  const submitSearch = (event: FormEvent) => {
    event.preventDefault()
    const value = query.trim()
    if (!value) return
    navigate(`/market?search=${encodeURIComponent(value)}`)
    setQuery('')
  }

  const openLocation = () => {
    setDraftLocation(location)
    setLocationOpen((current) => !current)
    setProfileOpen(false)
  }

  const applyLocation = () => {
    setLocation(draftLocation)
    persistMarketLocation(draftLocation)
    setLocationOpen(false)
  }

  const filteredStates = states.filter((item) => item.name.toLowerCase().includes(marketSearch.toLowerCase()))
  const filteredDistricts = districts.filter((item) => item.name.toLowerCase().includes(marketSearch.toLowerCase()))
  const selectedMarketLabel = location.market || location.city || location.state

  return (
    <div className="pb-app-shell">
      <header className="pb-header">
        <div className="pb-header-top">
          <button className="pb-mobile-menu" type="button" onClick={() => setMobileOpen(true)} aria-label="Open menu">
            <Menu size={23} />
          </button>

          <NavLink to="/" className="pb-brand" aria-label="TuberIntel home">
            <span className="pb-brand-mascot">
              <img src="/brand/tuber-mitra.png" alt="TuberIntel mascot" />
            </span>
            <span>
              <strong>TuberIntel</strong>
              <small>Potato decision intelligence</small>
            </span>
          </NavLink>

          <div className="pb-location-wrap" ref={locationWrapRef}>
            <button className="pb-location-button" type="button" onClick={openLocation} aria-expanded={locationOpen}>
              <span className="pb-location-icon">
                <MapPin size={18} />
              </span>
              <span className="pb-location-copy">
                <small>{copy.location}</small>
                <strong>{selectedMarketLabel}</strong>
                <em>{location.city ? `${location.city}, ` : ''}{location.state}</em>
              </span>
              <ChevronDown size={16} />
            </button>
            {locationOpen && (
              <div className="pb-location-popover pb-location-directory">
                <div className="pb-popover-heading">
                  <span className="pb-popover-icon">
                    <Landmark size={18} />
                  </span>
                  <div>
                    <strong>{copy.location}</strong>
                    <small>{draftLocation.market || draftLocation.city || draftLocation.state}</small>
                  </div>
                </div>
                <label className="pb-popover-search">
                  <Search size={16} />
                  <input
                    value={marketSearch}
                    onChange={(event) => setMarketSearch(event.target.value)}
                    placeholder={copy.search}
                  />
                </label>
                <div className="pb-directory-columns">
                  <div>
                    <span>{copy.state}</span>
                    <div className="pb-directory-list">
                      {filteredStates.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className={draftLocation.state === item.name ? 'active' : ''}
                          onClick={() => setDraftLocation({ state: item.name, city: '', market: '' })}
                        >
                          <strong>{item.name}</strong>
                          <small>{item.market_count} markets</small>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span>{copy.district}</span>
                    <div className="pb-directory-list">
                      {filteredDistricts.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className={draftLocation.city === item.name ? 'active' : ''}
                          onClick={() => setDraftLocation((current) => ({ ...current, city: item.name, market: '' }))}
                        >
                          <strong>{item.name}</strong>
                          <small>{item.market_count} markets</small>
                        </button>
                      ))}
                    </div>
                  </div>
                  <div>
                    <span>{copy.market}</span>
                    <div className="pb-directory-list">
                      {markets.map((item) => (
                        <button
                          key={item.id}
                          type="button"
                          className={draftLocation.market === item.name ? 'active' : ''}
                          onClick={() =>
                            setDraftLocation({
                              state: item.state,
                              city: item.district,
                              market: item.name,
                            })
                          }
                        >
                          <strong>{item.name}</strong>
                          <small>{item.district}, {item.state}</small>
                        </button>
                      ))}
                      {!markets.length && !loadingLocation && <div className="pb-directory-empty">{copy.empty}</div>}
                      {loadingLocation && <div className="pb-directory-empty">{copy.loading}</div>}
                    </div>
                  </div>
                </div>
                <button className="pb-location-apply" type="button" onClick={applyLocation}>
                  {copy.apply}
                </button>
              </div>
            )}
          </div>

          <form className="pb-global-search" onSubmit={submitSearch}>
            <Search size={19} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder={copy.search} />
          </form>

          <div className="pb-header-actions">
            <button className="pb-icon-button" type="button" title="Notifications">
              <Bell size={20} />
              <span className="pb-notification-dot" />
            </button>
            <div className="pb-profile-wrap" ref={profileWrapRef}>
              <button
                className="pb-profile-button"
                type="button"
                onClick={() => {
                  setProfileOpen((value) => !value)
                  setLocationOpen(false)
                }}
              >
                {user?.avatarUrl ? <img src={user.avatarUrl} alt="" /> : <span><UserRound size={20} /></span>}
                <div>
                  <strong>{user?.name || 'TuberIntel user'}</strong>
                  <small className="pb-profile-email">{user?.email || copy.account}</small>
                </div>
                <ChevronDown size={16} />
              </button>
              {profileOpen && (
                <div className="pb-profile-popover">
                  <div className="pb-profile-summary">
                    {user?.avatarUrl ? <img src={user.avatarUrl} alt="" /> : <span><UserRound size={22} /></span>}
                    <div>
                      <strong>{user?.name || 'TuberIntel user'}</strong>
                      <small>{user?.email}</small>
                    </div>
                  </div>
                  <button type="button" onClick={() => setLanguage(language === 'en' ? 'kn' : 'en')}>
                    <Languages size={17} />
                    {language === 'en' ? 'ಕನ್ನಡ' : 'English'}
                  </button>
                  <NavLink to="/models" onClick={() => setProfileOpen(false)}>
                    <Settings size={17} />
                    {copy.models}
                  </NavLink>
                  <button className="danger" type="button" onClick={() => void signOut()}>
                    <LogOut size={17} />
                    {copy.signOut}
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        <nav className="pb-primary-nav" aria-label="Primary navigation">
          <div className="pb-primary-nav-inner">
            {primaryNav.map(({ to, label, icon: Icon }) => (
              <NavLink key={to} to={to} end={to === '/'}>
                <Icon size={17} />
                <span>{label}</span>
              </NavLink>
            ))}
            <div className="pb-more-menu">
              <button type="button">
                <Menu size={17} />
                <span>{copy.more}</span>
                <ChevronDown size={15} />
              </button>
              <div className="pb-more-popover">
                {moreNav.map(({ label, icon: Icon }) => (
                  <span key={label}>
                    <Icon size={17} />
                    {label}
                    <small>Coming soon</small>
                  </span>
                ))}
              </div>
            </div>
          </div>
        </nav>
      </header>

      <aside className={`pb-mobile-drawer ${mobileOpen ? 'open' : ''}`}>
        <div className="pb-mobile-drawer-head">
          <div className="pb-brand">
            <span className="pb-brand-mascot">
              <img src="/brand/tuber-mitra.png" alt="" />
            </span>
            <span>
              <strong>TuberIntel</strong>
              <small>Potato decision intelligence</small>
            </span>
          </div>
          <button type="button" onClick={() => setMobileOpen(false)}>
            <X size={22} />
          </button>
        </div>
        <button className="pb-drawer-location" type="button" onClick={() => { setMobileOpen(false); openLocation() }}>
          <MapPin size={18} />
          <span>
            <small>{copy.location}</small>
            <strong>{selectedMarketLabel}, {location.state}</strong>
          </span>
          <ChevronDown size={16} />
        </button>
        <nav>
          {primaryNav.map(({ to, label, icon: Icon }) => (
            <NavLink key={to} to={to} end={to === '/'} onClick={() => setMobileOpen(false)}>
              <Icon size={19} />
              {label}
            </NavLink>
          ))}
          {moreNav.map(({ label, icon: Icon }) => (
            <span className="disabled" key={label}>
              <Icon size={19} />
              {label}
              <small>Coming soon</small>
            </span>
          ))}
        </nav>
        <button className="pb-drawer-signout" type="button" onClick={() => void signOut()}>
          <LogOut size={18} />
          {copy.signOut}
        </button>
      </aside>
      {mobileOpen && <button className="pb-drawer-backdrop" type="button" aria-label="Close menu" onClick={() => setMobileOpen(false)} />}

      <main className="pb-main">
        <Outlet />
      </main>

      <nav className="pb-mobile-bottom-nav" aria-label="Mobile navigation">
        {primaryNav.slice(0, 4).map(({ to, label, icon: Icon }) => (
          <NavLink key={to} to={to} end={to === '/'}>
            <Icon size={20} />
            <span>{label}</span>
          </NavLink>
        ))}
        <button type="button" onClick={() => setMobileOpen(true)}>
          <Menu size={20} />
          <span>{copy.more}</span>
        </button>
      </nav>
    </div>
  )
}
