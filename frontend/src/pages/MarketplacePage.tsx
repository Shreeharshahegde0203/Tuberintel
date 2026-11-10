import {
  BadgeCheck,
  Building2,
  Heart,
  MapPin,
  PackageSearch,
  Plus,
  RefreshCw,
  Search,
  SlidersHorizontal,
  Truck,
  X,
} from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { PageHeader } from '../components/Common'
import { readMarketLocation } from '../data/marketLocations'
import { useI18n } from '../i18n/I18nContext'
import {
  createTradeListing,
  getBatches,
  getColdStorage,
  getMarketplaceSummary,
  getTradeListings,
  getTransportProviders,
  setTradeFavorite,
  updateTradeListing,
} from '../services/api'
import type {
  BatchListItem,
  ColdStorageFacility,
  MarketplaceSummary,
  TradeListing,
  TransportProvider,
} from '../types'

type ViewMode = 'SELL' | 'BUY' | 'favorites' | 'mine'

const money = new Intl.NumberFormat('en-IN', { maximumFractionDigits: 0 })

export default function MarketplacePage() {
  const { user } = useAuth()
  const { language } = useI18n()
  const location = readMarketLocation()
  const [view, setView] = useState<ViewMode>('SELL')
  const [summary, setSummary] = useState<MarketplaceSummary | null>(null)
  const [listings, setListings] = useState<TradeListing[]>([])
  const [batches, setBatches] = useState<BatchListItem[]>([])
  const [coldStores, setColdStores] = useState<ColdStorageFacility[]>([])
  const [transport, setTransport] = useState<TransportProvider[]>([])
  const [search, setSearch] = useState('')
  const [state, setState] = useState(location.state || '')
  const [variety, setVariety] = useState('')
  const [sort, setSort] = useState('newest')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [composer, setComposer] = useState(false)
  const [form, setForm] = useState({
    listing_type: 'SELL' as 'BUY' | 'SELL',
    owner_name: user?.name || 'Farmer',
    contact_phone: user?.phone || '',
    variety: 'Kufri Jyoti',
    quantity_kg: 1000,
    price_per_quintal: 2100,
    state: location.state || 'Karnataka',
    district: location.district || 'Kolar',
    location: location.market || location.district || 'Kolar APMC belt',
    notes: '',
    source_batch_id: '' as string | number,
  })

  const copy = language === 'kn'
    ? {
        eyebrow: 'ವ್ಯಾಪಾರ ಜಾಲ', title: 'ಮಾರುಕಟ್ಟೆ',
        description: 'ಗುಣಮಟ್ಟ ಪರಿಶೀಲಿಸಿದ ಲಾಟ್‌ಗಳನ್ನು ಪ್ರಕಟಿಸಿ, ಖರೀದಿ ಬೇಡಿಕೆಗಳನ್ನು ನೋಡಿ ಮತ್ತು ಸೇವೆಗಳನ್ನು ಕಂಡುಹಿಡಿಯಿರಿ.',
        sellers: 'ಮಾರಾಟಗಾರರನ್ನು ಹುಡುಕಿ', buyers: 'ಖರೀದಿದಾರರನ್ನು ಹುಡುಕಿ', favorites: 'ಉಳಿಸಿದವು', mine: 'ನನ್ನ ಪೋಸ್ಟ್‌ಗಳು',
        newPost: 'ಹೊಸ ಪೋಸ್ಟ್', verified: 'TuberIntel ಪರಿಶೀಲಿತ', demo: 'ಡೆಮೊ ಪೋಸ್ಟ್', quantity: 'ಪ್ರಮಾಣ',
        price: 'ಬೆಲೆ / ಕ್ವಿಂಟಲ್', contact: 'ಸಂಪರ್ಕ', close: 'ಪೋಸ್ಟ್ ಮುಚ್ಚಿ', noPosts: 'ಈ ಫಿಲ್ಟರ್‌ಗೆ ಯಾವುದೇ ಸಕ್ರಿಯ ಪೋಸ್ಟ್‌ಗಳಿಲ್ಲ.',
        services: 'ಲಾಗಿಸ್ಟಿಕ್ಸ್ ಮತ್ತು ಸಂಗ್ರಹ ಸೇವೆಗಳು', cold: 'ಕೋಲ್ಡ್ ಸ್ಟೋರೇಜ್', transport: 'ಸಾಗಣೆ',
      }
    : {
        eyebrow: 'Trade network', title: 'Marketplace',
        description: 'Buy requirements, sell lots, quality context, storage and transport in one operational view.',
        sellers: 'Sell lots', buyers: 'Buy requirements', favorites: 'Saved', mine: 'My postings',
        newPost: 'New post', verified: 'TuberIntel verified', demo: 'Demo post', quantity: 'Quantity',
        price: 'Price / quintal', contact: 'Contact', close: 'Close post', noPosts: 'No active posts match these filters.',
        services: 'Logistics & storage services', cold: 'Cold storage', transport: 'Transport',
      }

  const load = async () => {
    setBusy(true)
    setError('')
    try {
      const params: Record<string, string | boolean> = { sort }
      if (view === 'SELL' || view === 'BUY') params.listing_type = view
      if (view === 'favorites') params.favorites_only = true
      if (view === 'mine') params.only_owner = true
      if (search.trim()) params.search = search.trim()
      if (state) params.state = state
      if (variety) params.variety = variety
      const [s, page, batchRows, stores, transportRows] = await Promise.all([
        getMarketplaceSummary(),
        getTradeListings(params),
        getBatches(),
        getColdStorage(state || undefined),
        getTransportProviders(state || undefined),
      ])
      setSummary(s)
      setListings(page.items)
      setBatches(batchRows.filter((item) => item.status === 'analyzed' && item.grade))
      setColdStores(stores)
      setTransport(transportRows)
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Could not load trade network')
    } finally {
      setBusy(false)
    }
  }

  useEffect(() => { void load() }, [view, state, variety, sort])

  const selectedBatch = useMemo(
    () => batches.find((item) => item.id === Number(form.source_batch_id)),
    [batches, form.source_batch_id],
  )

  const chooseBatch = (batchId: string) => {
    const batch = batches.find((item) => item.id === Number(batchId))
    setForm((current) => ({
      ...current,
      source_batch_id: batchId,
      variety: batch?.variety || current.variety,
      quantity_kg: batch ? Math.min(current.quantity_kg, batch.quantity_kg) : current.quantity_kg,
    }))
  }

  const submitPost = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true); setError('')
    try {
      await createTradeListing({
        listing_type: form.listing_type,
        owner_name: form.owner_name,
        contact_phone: form.contact_phone || null,
        variety: form.variety,
        quantity_kg: Number(form.quantity_kg),
        price_per_quintal: Number(form.price_per_quintal),
        state: form.state,
        district: form.district,
        location: form.location,
        notes: form.notes || null,
        source_batch_id: form.source_batch_id ? Number(form.source_batch_id) : null,
      }, crypto.randomUUID())
      setComposer(false)
      setView(form.listing_type)
      await load()
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || 'Could not publish post')
    } finally { setBusy(false) }
  }

  const toggleFavorite = async (listing: TradeListing) => {
    try {
      await setTradeFavorite(listing.id, !listing.is_favorite)
      setListings((rows) => rows.map((row) => row.id === listing.id ? { ...row, is_favorite: !row.is_favorite } : row))
    } catch (err: any) { setError(err?.response?.data?.detail || err.message) }
  }

  const closePost = async (listing: TradeListing) => {
    try {
      await updateTradeListing(listing.id, { status: 'CLOSED' })
      setListings((rows) => rows.filter((row) => row.id !== listing.id))
    } catch (err: any) { setError(err?.response?.data?.detail || err.message) }
  }

  return <>
    <PageHeader eyebrow={copy.eyebrow} title={copy.title} description={copy.description} actions={
      <button className="button button-primary" type="button" onClick={() => setComposer(true)}><Plus size={18} />{copy.newPost}</button>
    } />

    <section className="trade-summary-grid">
      <article><span>Sell posts</span><strong>{summary?.active_sell_posts ?? '—'}</strong></article>
      <article><span>Buy requirements</span><strong>{summary?.active_buy_posts ?? '—'}</strong></article>
      <article><span>Quality-linked</span><strong>{summary?.verified_quality_posts ?? '—'}</strong></article>
    </section>

    <section className="panel trade-workspace">
      <div className="trade-tabs">
        <button className={view === 'SELL' ? 'active' : ''} onClick={() => setView('SELL')}>{copy.sellers}</button>
        <button className={view === 'BUY' ? 'active' : ''} onClick={() => setView('BUY')}>{copy.buyers}</button>
        <button className={view === 'favorites' ? 'active' : ''} onClick={() => setView('favorites')}><Heart size={15} />{copy.favorites}</button>
        <button className={view === 'mine' ? 'active' : ''} onClick={() => setView('mine')}>{copy.mine}</button>
      </div>

      <div className="trade-filterbar">
        <label className="trade-search"><Search size={17} /><input value={search} onChange={(e) => setSearch(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') void load() }} placeholder="Variety, district, farmer…" /><button onClick={() => void load()} type="button">Search</button></label>
        <label><SlidersHorizontal size={15} /><select value={state} onChange={(e) => setState(e.target.value)}><option value="">All states</option>{(summary?.states || []).map((item) => <option key={item}>{item}</option>)}</select></label>
        <label><select value={variety} onChange={(e) => setVariety(e.target.value)}><option value="">All varieties</option>{(summary?.varieties || []).map((item) => <option key={item}>{item}</option>)}</select></label>
        <label><select value={sort} onChange={(e) => setSort(e.target.value)}><option value="newest">Newest</option><option value="price_low">Lowest price</option><option value="price_high">Highest price</option><option value="quantity_high">Largest quantity</option></select></label>
        <button className="trade-refresh" title="Refresh" onClick={() => void load()} disabled={busy}><RefreshCw className={busy ? 'spin' : ''} size={17} /></button>
      </div>

      {error && <div className="inline-error trade-error">{typeof error === 'string' ? error : JSON.stringify(error)}</div>}
      <div className="trade-listings">
        {listings.map((listing) => <article className="trade-card" key={listing.id}>
          <div className="trade-card-head">
            <div><span className={`trade-type ${listing.listing_type.toLowerCase()}`}>{listing.listing_type === 'SELL' ? 'FOR SALE' : 'WANTED'}</span><strong>{listing.variety}</strong></div>
            <button className={`trade-heart ${listing.is_favorite ? 'active' : ''}`} onClick={() => void toggleFavorite(listing)} aria-label="Favorite"><Heart size={18} fill={listing.is_favorite ? 'currentColor' : 'none'} /></button>
          </div>
          <div className="trade-numbers"><div><span>{copy.quantity}</span><strong>{(listing.quantity_kg / 100).toFixed(1)} q</strong></div><div><span>{copy.price}</span><strong>₹{money.format(listing.price_per_quintal)}</strong></div></div>
          <div className="trade-location"><MapPin size={15} />{listing.location}, {listing.district}, {listing.state}</div>
          {listing.verified_quality ? <div className="trade-quality"><BadgeCheck size={17} /><div><strong>{copy.verified}</strong><span>Grade {listing.quality_grade} · {listing.quality_score?.toFixed(1)}/100 · {listing.size_class}</span></div></div> : <div className="trade-demo"><PackageSearch size={15} />{listing.is_demo ? copy.demo : 'Seller-provided quality'}</div>}
          {listing.notes && <p>{listing.notes}</p>}
          <footer><div><strong>{listing.owner_name}</strong><span>{new Date(listing.created_at).toLocaleDateString('en-IN')}</span></div>{listing.is_owner ? <button className="trade-close" onClick={() => void closePost(listing)}>{copy.close}</button> : listing.contact_phone ? <a href={`tel:${listing.contact_phone}`}>{copy.contact}</a> : <span className="trade-no-contact">Demo / no contact</span>}</footer>
        </article>)}
        {!busy && listings.length === 0 && <div className="trade-empty"><PackageSearch size={28} /><strong>{copy.noPosts}</strong><span>Try removing a location or variety filter.</span></div>}
      </div>
    </section>

    <section className="trade-services-section" id="services">
      <div className="trade-section-heading"><div><span>Support network</span><h2>{copy.services}</h2></div><small>Seeded entries are clearly marked as demo until a verified provider API/directory is connected.</small></div>
      <div className="trade-services-grid">
        <div className="panel"><h3><Building2 size={19} />{copy.cold}</h3>{coldStores.slice(0, 4).map((item) => <article className="trade-service" key={item.id}><div><strong>{item.name}</strong><span>{item.location}, {item.district}</span></div><div><strong>{money.format(item.available_capacity_tonnes)} t free</strong><span>₹{item.estimated_cost_per_quintal_day}/q/day · demo</span></div></article>)}</div>
        <div className="panel"><h3><Truck size={19} />{copy.transport}</h3>{transport.slice(0, 4).map((item) => <article className="trade-service" key={item.id}><div><strong>{item.name}</strong><span>{item.base_location}, {item.district}</span></div><div><strong>₹{item.rate_per_km_tonne}/km/t</strong><span>{item.vehicle_types.join(' · ')} · demo</span></div></article>)}</div>
      </div>
    </section>

    {composer && <div className="trade-modal-backdrop" role="presentation"><div className="trade-modal" role="dialog" aria-modal="true" aria-label="Create trade post">
      <div className="trade-modal-head"><div><span>Trade post</span><h2>Publish a requirement</h2></div><button onClick={() => setComposer(false)}><X size={20} /></button></div>
      <form onSubmit={submitPost} className="trade-form">
        <label><span>Post type</span><select value={form.listing_type} onChange={(e) => setForm((c) => ({ ...c, listing_type: e.target.value as 'BUY' | 'SELL' }))}><option value="SELL">I want to sell</option><option value="BUY">I want to buy</option></select></label>
        <label><span>Name</span><input required value={form.owner_name} onChange={(e) => setForm((c) => ({ ...c, owner_name: e.target.value }))} /></label>
        <label><span>Phone</span><input value={form.contact_phone} onChange={(e) => setForm((c) => ({ ...c, contact_phone: e.target.value }))} /></label>
        <label className="span-2"><span>Attach analyzed batch (optional, sell posts)</span><select value={form.source_batch_id} onChange={(e) => chooseBatch(e.target.value)}><option value="">No batch attached</option>{batches.map((batch) => <option value={batch.id} key={batch.id}>{batch.batch_code} · {batch.variety} · Grade {batch.grade}</option>)}</select>{selectedBatch && <small>This post will inherit the analyzed grade and variety from {selectedBatch.batch_code}.</small>}</label>
        <label><span>Variety</span><input required value={form.variety} onChange={(e) => setForm((c) => ({ ...c, variety: e.target.value }))} /></label>
        <label><span>Quantity (kg)</span><input required type="number" min="1" value={form.quantity_kg} onChange={(e) => setForm((c) => ({ ...c, quantity_kg: Number(e.target.value) }))} /></label>
        <label><span>Price (₹/quintal)</span><input required type="number" min="1" value={form.price_per_quintal} onChange={(e) => setForm((c) => ({ ...c, price_per_quintal: Number(e.target.value) }))} /></label>
        <label><span>State</span><input required value={form.state} onChange={(e) => setForm((c) => ({ ...c, state: e.target.value }))} /></label>
        <label><span>District</span><input required value={form.district} onChange={(e) => setForm((c) => ({ ...c, district: e.target.value }))} /></label>
        <label><span>Location</span><input required value={form.location} onChange={(e) => setForm((c) => ({ ...c, location: e.target.value }))} /></label>
        <label className="span-2"><span>Notes / buyer specification</span><textarea rows={3} value={form.notes} onChange={(e) => setForm((c) => ({ ...c, notes: e.target.value }))} /></label>
        <div className="trade-form-actions span-2"><button type="button" className="button button-secondary" onClick={() => setComposer(false)}>Cancel</button><button type="submit" className="button button-primary" disabled={busy}>{busy ? 'Publishing…' : 'Publish post'}</button></div>
      </form>
    </div></div>}
  </>
}
