import axios from 'axios'

import { getAccessToken } from '../auth/AuthContext'
import type {
  Batch,
  BatchListItem,
  DashboardSummary,
  MandiDirectoryResponse,
  MarketAnalytics,
  MarketDistrictOption,
  MarketFilters,
  MarketOverview,
  MarketPrice,
  MarketStateOption,
  MarketSyncResponse,
  ModelStatusResponse,
  NewsResponse,
  StoragePlanPayload,
  StoragePlanResult,
  TransportPlanPayload,
  TransportPlanResult,
  WeatherResponse,
} from '../types'

const apiBase = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1'

export const mediaBase = import.meta.env.VITE_MEDIA_URL || ''

export const api = axios.create({
  baseURL: apiBase,
  timeout: 30_000,
  headers: {
    Accept: 'application/json',
  },
})

api.interceptors.request.use(async (config) => {
  const token = await getAccessToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.Authorization = `Bearer ${token}`
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
  storage_cost_per_quintal_day: number
  storage_days: number
  transport_cost_per_km_tonne: number
  distance_km: number
  processor_price_per_quintal?: number | null
  handling_cost_per_quintal: number
  target_margin_percent: number
  language?: 'en' | 'kn'
}

export type MarketPriceQuery = {
  state?: string
  district?: string
  market?: string
  commodity?: string
  variety?: string
  grade?: string
  date_from?: string
  date_to?: string
  latest_only?: boolean
  limit?: number
  offset?: number
}

export type MarketAnalyticsQuery = {
  state?: string
  district?: string
  market?: string
  commodity?: string
  variety?: string
  window_days?: number
}

export async function getDashboard() {
  const response = await api.get<DashboardSummary>('/dashboard')
  return response.data
}

export async function createBatch(payload: CreateBatchPayload) {
  const response = await api.post<Batch>('/batches', payload)
  return response.data
}

export async function uploadBatchImages(batchId: number, files: File[]) {
  const body = new FormData()
  files.forEach((file) => {
    body.append('files', file)
  })
  const response = await api.post<Batch>(`/batches/${batchId}/images`, body, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

export async function analyzeBatch(batchId: number, options: AnalysisOptionsPayload) {
  const response = await api.post<Batch>(`/batches/${batchId}/analyze`, options)
  return response.data
}

export async function getBatch(batchId: number) {
  const response = await api.get<Batch>(`/batches/${batchId}`)
  return response.data
}

export async function getBatches() {
  const response = await api.get<BatchListItem[]>('/batches')
  return response.data
}

export async function getMarketOverview(state = 'Karnataka') {
  const response = await api.get<MarketOverview>('/market/overview', {
    params: { state },
  })
  return response.data
}

export async function getMandiStates() {
  const response = await api.get<MarketStateOption[]>('/market/directory/states')
  return response.data
}

export async function getMandiDistricts(state: string) {
  const response = await api.get<MarketDistrictOption[]>('/market/directory/districts', {
    params: { state },
  })
  return response.data
}

export async function getMandiDirectory(
  state?: string,
  district?: string,
  search?: string,
  limit = 50,
  offset = 0,
) {
  const response = await api.get<MandiDirectoryResponse>('/market/directory/mandis', {
    params: {
      state: state || undefined,
      district: district || undefined,
      search: search || undefined,
      limit,
      offset,
    },
  })
  return response.data
}

export async function syncMandiDirectory(state?: string) {
  const response = await api.post<MarketSyncResponse>('/admin/market/directory/sync', null, {
    params: {
      state: state || undefined,
    },
  })
  return response.data
}

export async function getMarketFilters(state?: string, district?: string) {
  const response = await api.get<MarketFilters>('/market/filters', {
    params: {
      state: state || undefined,
      district: district || undefined,
    },
  })
  return response.data
}

export async function getMarketPrices(params: MarketPriceQuery = {}) {
  const response = await api.get<MarketPrice[]>('/market/prices', {
    params,
  })
  return response.data
}

export async function getMarketAnalytics(params: MarketAnalyticsQuery = {}) {
  const response = await api.get<MarketAnalytics>('/market/analytics', {
    params,
  })
  return response.data
}

export async function refreshMarket(state = 'Karnataka', maxPages = 3) {
  const response = await api.post<MarketSyncResponse>('/admin/market/prices/refresh', null, {
    params: {
      state,
      max_pages: maxPages,
    },
  })
  return response.data
}

export async function getWeather(latitude: number, longitude: number, days = 5) {
  const response = await api.get<WeatherResponse>('/weather', {
    params: {
      latitude,
      longitude,
      days,
    },
  })
  return response.data
}

export async function getNews(params: { category?: string; search?: string; limit?: number; refresh?: boolean } = {}) {
  const response = await api.get<NewsResponse>('/news', { params })
  return response.data
}

export async function calculateStoragePlan(payload: StoragePlanPayload) {
  const response = await api.post<StoragePlanResult>('/tools/storage-plan', payload)
  return response.data
}

export async function calculateTransportPlan(payload: TransportPlanPayload) {
  const response = await api.post<TransportPlanResult>('/tools/transport-plan', payload)
  return response.data
}

export async function getModelStatus() {
  const response = await api.get<ModelStatusResponse>('/models')
  return response.data
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
  const response = await api.post(`/batches/${batchId}/feedback`, payload)
  return response.data
}
