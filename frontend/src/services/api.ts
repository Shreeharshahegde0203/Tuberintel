import axios from 'axios'
import type {
  Batch,
  BatchListItem,
  DashboardSummary,
  MarketAnalytics,
  MandiDirectoryResponse,
  MarketFilters,
  MarketOverview,
  MarketStateOption,
  MarketPrice,
  ModelStatusResponse,
  NewsResponse,
  StoragePlanPayload,
  StoragePlanResult,
  TransportPlanPayload,
  TransportPlanResult,
  WeatherResponse,
  AssistantReply,
  ColdStorageFacility,
  MarketplaceSummary,
  TradeListing,
  TradeListingCreate,
  TradeListingPage,
  TransportProvider,
} from '../types'

const apiBase = import.meta.env.VITE_API_URL || '/api/v1'

export const mediaBase = import.meta.env.VITE_MEDIA_URL || ''

export const api = axios.create({
  baseURL: apiBase,
  timeout: 120_000,
})

api.interceptors.request.use((config) => {
  try {
    const raw = localStorage.getItem('tuberintel-session')
    if (raw) {
      const session = JSON.parse(raw) as { user?: { id?: string }; access_token?: string }
      if (session.user?.id) config.headers.set('X-User-Ref', session.user.id)
      if (session.access_token) config.headers.set('Authorization', `Bearer ${session.access_token}`)
    }
  } catch {
    // Authentication state remains owned by AuthContext.
  }
  return config
})

export type CreateBatchPayload = {
  variety: string
  quantity_kg: number
  farmer_name?: string
  source_location: string
  state: string
  district?: string
  harvest_date?: string
  intended_market?: string
}

export type AnalysisOptionsPayload = {
  quality_pricing_mode?: 'estimated' | 'manual' | 'reference'
  fresh_buyer_price_per_quintal?: number | null
  buyer_quality_discount_percent?: number | null
  saleable_weight_percent?: number | null
  storage_cost_per_quintal_day: number
  storage_days: number
  transport_cost_per_km_tonne: number
  distance_km: number
  processor_price_per_quintal?: number | null
  handling_cost_per_quintal: number
  target_margin_percent: number
  language?: 'en' | 'kn'
  measured_length_mm?: number | null
  measured_width_mm?: number | null
  measurement_source?: 'not_available' | 'manual' | 'potato_ruler' | 'calibrated_image'
}

export async function getDashboard() {
  const { data } = await api.get<DashboardSummary>('/dashboard')
  return data
}

export async function createBatch(payload: CreateBatchPayload) {
  const { data } = await api.post<Batch>('/batches', payload)
  return data
}

export async function uploadBatchImages(batchId: number, files: File[]) {
  const body = new FormData()
  files.forEach((file) => body.append('files', file))
  const { data } = await api.post<Batch>(`/batches/${batchId}/images`, body, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function analyzeBatch(batchId: number, options: AnalysisOptionsPayload) {
  const { data } = await api.post<Batch>(`/batches/${batchId}/analyze`, options)
  return data
}

export async function getBatch(batchId: number) {
  const { data } = await api.get<Batch>(`/batches/${batchId}`)
  return data
}

export async function getBatches() {
  const { data } = await api.get<BatchListItem[]>('/batches')
  return data
}

export async function getMarketOverview(state = 'Karnataka') {
  const { data } = await api.get<MarketOverview>('/market/overview', { params: { state } })
  return data
}

export async function getMandiStates() {
  const { data } = await api.get<MarketStateOption[]>('/market/directory/states')
  return data
}

export async function getMandiDirectory(state: string, district?: string, search?: string) {
  const { data } = await api.get<MandiDirectoryResponse>('/market/directory/mandis', {
    params: { state, district: district || undefined, search: search || undefined, limit: 5000 },
  })
  return data
}

export async function syncMandiDirectory(state: string, maxPages?: number) {
  const { data } = await api.post<{
    state: string
    received: number
    inserted: number
    updated: number
    mandi_count: number
    live_data: boolean
    source: string
    note: string
  }>('/market/directory/sync', null, { params: { state, max_pages: maxPages } })
  return data
}

export async function getMarketFilters(state?: string) {
  const { data } = await api.get<MarketFilters>('/market/filters', { params: state ? { state } : {} })
  return data
}

export async function getMarketPrices(params: {
  state?: string
  district?: string
  market?: string
  variety?: string
  grade?: string
  date_from?: string
  date_to?: string
  latest_only?: boolean
  limit?: number
  offset?: number
} = {}) {
  const { data } = await api.get<MarketPrice[]>('/market/prices', { params })
  return data
}

export async function getMarketAnalytics(params: {
  state?: string
  district?: string
  market?: string
  variety?: string
  window_days?: number
} = {}) {
  const { data } = await api.get<MarketAnalytics>('/market/analytics', { params })
  return data
}

export async function refreshMarket(state = 'Karnataka', district?: string) {
  const { data } = await api.post<{
    updated: number
    inserted: number
    received: number
    source: string
    live_data: boolean
    note: string
  }>('/market/refresh', null, { params: { state, district } })
  return data
}

export async function getNews(params: { category?: string; search?: string; limit?: number; refresh?: boolean } = {}) {
  const { data } = await api.get<NewsResponse>('/news', { params })
  return data
}

export async function refreshNews() {
  const { data } = await api.post('/news/refresh')
  return data
}

export async function getWeather(latitude: number, longitude: number, days = 5) {
  const { data } = await api.get<WeatherResponse>('/weather', { params: { latitude, longitude, days } })
  return data
}

export async function calculateStoragePlan(payload: StoragePlanPayload) {
  const { data } = await api.post<StoragePlanResult>('/tools/storage-plan', payload)
  return data
}

export async function calculateTransportPlan(payload: TransportPlanPayload) {
  const { data } = await api.post<TransportPlanResult>('/tools/transport-plan', payload)
  return data
}

export async function getModelStatus() {
  const { data } = await api.get<ModelStatusResponse>('/models')
  return data
}

export async function submitFeedback(
  batchId: number,
  payload: {
    action_taken: string
    actual_price_per_quintal?: number | null
    actual_profit?: number | null
    rating: number
    notes?: string
  },
) {
  const { data } = await api.post(`/batches/${batchId}/feedback`, payload)
  return data
}


export async function getMarketplaceSummary() {
  const { data } = await api.get<MarketplaceSummary>('/marketplace/summary')
  return data
}

export async function getTradeListings(params: Record<string, string | number | boolean | undefined> = {}) {
  const { data } = await api.get<TradeListingPage>('/marketplace/listings', { params })
  return data
}

export async function createTradeListing(payload: TradeListingCreate, idempotencyKey: string) {
  const { data } = await api.post<TradeListing>('/marketplace/listings', payload, { headers: { 'Idempotency-Key': idempotencyKey } })
  return data
}

export async function updateTradeListing(listingId: number, payload: { status?: 'ACTIVE' | 'CLOSED'; price_per_quintal?: number; quantity_kg?: number; notes?: string }) {
  const { data } = await api.patch<TradeListing>(`/marketplace/listings/${listingId}`, payload)
  return data
}

export async function setTradeFavorite(listingId: number, favorite: boolean) {
  if (favorite) {
    const { data } = await api.post<{ listing_id: number; favorite: boolean }>(`/marketplace/listings/${listingId}/favorite`)
    return data
  }
  const { data } = await api.delete<{ listing_id: number; favorite: boolean }>(`/marketplace/listings/${listingId}/favorite`)
  return data
}

export async function getColdStorage(state?: string, district?: string) {
  const { data } = await api.get<ColdStorageFacility[]>('/marketplace/cold-storage', { params: { state, district } })
  return data
}

export async function getTransportProviders(state?: string, district?: string) {
  const { data } = await api.get<TransportProvider[]>('/marketplace/transport', { params: { state, district } })
  return data
}

export async function askFarmerAssistant(payload: { message: string; language?: 'en' | 'kn'; batch_id?: number; state?: string; district?: string }) {
  const { data } = await api.post<AssistantReply>('/assistant/query', payload)
  return data
}

export interface ForecastPoint {
  date: string
  predicted_price: number
  lower_bound: number
  upper_bound: number
  horizon_days: number | null
  model_name: string | null
  confidence: string | null
  interval_level: number | null
}

export interface MarketForecastResponse {
  state: string
  district: string | null
  market: string | null
  variety: string | null
  horizon_days: number
  points: ForecastPoint[]
  model_name: string
  model_version: string
  confidence: string
  training_points: number
  fallback_used: boolean
  data_start: string | null
  data_end: string | null
  methodology: string[]
  diagnostics: Record<string, unknown>
}

export interface MarketForecastParams {
  state?: string
  district?: string
  market?: string
  variety?: string
  horizon_days?: number
}

export async function getMarketForecast(
  params: MarketForecastParams = {}
): Promise<MarketForecastResponse> {
  const { data } = await api.get<MarketForecastResponse>(
    "/market/forecast",
    { params }
  )

  return data
}