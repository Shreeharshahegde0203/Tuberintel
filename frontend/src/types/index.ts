export type ForecastPoint = {
  date: string
  predicted_price: number
  lower_bound: number
  upper_bound: number
}

export type MarketPrice = {
  id: number
  market_id: number | null
  state: string
  district: string
  market: string
  commodity: string
  variety: string
  grade: string
  arrival_date: string
  min_price: number
  max_price: number
  modal_price: number
  source: string
  fetched_at: string
  source_record_id: string | null
}

export type MarketConsolidated = {
  date: string | null
  active_mandis: number
  records: number
  average_modal_price: number | null
  minimum_price: number | null
  maximum_price: number | null
  commodity: string
  data_source: string
  arrival_volume: number | null
  arrival_volume_note: string
  change_percent_7d: number
  direction: 'rising' | 'falling' | 'stable'
}

export type TopMarketItem = {
  market_id: number | null
  state: string
  district: string
  market: string
  modal_price: number
  arrival_date: string
  variety: string
  source: string
  rank: number
  change_percent: number | null
}

export type MarketOverview = {
  latest_prices: MarketPrice[]
  forecast: ForecastPoint[]
  price_direction: 'rising' | 'falling' | 'stable'
  change_percent: number
  best_market: string
  source_note: string
  freshness: string
  consolidated: MarketConsolidated
  top_markets: TopMarketItem[]
  live_data: boolean
  states: string[]
}

export type MarketStateOption = {
  id: number
  name: string
  code: string | null
  active: boolean
  district_count: number
  market_count: number
}

export type MarketDistrictOption = {
  id: number
  name: string
  state: string
  active: boolean
  market_count: number
}

export type MandiDirectoryItem = {
  id: number
  name: string
  state: string
  district: string
  source: string
  active: boolean
  latitude: number | null
  longitude: number | null
  external_market_name: string | null
  external_id: string | null
  updated_at: string
}

export type MandiDirectoryResponse = {
  state: string | null
  district: string | null
  total: number
  limit: number
  offset: number
  items: MandiDirectoryItem[]
  source: string
  live_data: boolean
  note: string | null
}

export type MarketFilters = {
  states: string[]
  districts: string[]
  markets: string[]
  commodities: string[]
  varieties: string[]
  grades: string[]
  selected_state: string | null
  selected_district: string | null
  source: string | null
  freshness: string | null
}

export type MarketTrendPoint = {
  date: string
  min_price: number
  max_price: number
  modal_price: number
  average_price: number
}

export type MarketAnalyticsSummary = {
  record_count: number
  average_modal_price: number | null
  minimum_price: number | null
  maximum_price: number | null
  latest_price: number | null
  previous_price: number | null
  change_amount: number | null
  change_percent: number
  direction: 'rising' | 'falling' | 'stable'
}

export type MarketAnalytics = {
  state: string | null
  district: string | null
  market: string | null
  commodity: string
  variety: string | null
  window_days: number
  summary: MarketAnalyticsSummary
  trend: MarketTrendPoint[]
  source: string
  freshness: string
  note: string | null
}

export type WeatherForecastDay = {
  date: string
  minimum_temperature: number
  maximum_temperature: number
  precipitation_probability: number
}

export type WeatherCurrent = {
  current_temperature: number | null
  current_humidity: number | null
  current_wind_speed: number | null
  current_weather_code: number | null
}

export type WeatherResponse = {
  current: WeatherCurrent
  daily: WeatherForecastDay[]
  source: string
}

export type NewsItem = {
  id: number | string
  title: string
  category?: string
  source?: string
  published_at?: string | null
  url?: string
}

export type NewsResponse = {
  items: NewsItem[]
  articles?: NewsItem[]
  total: number
  source?: string
  live_data?: boolean
  note?: string | null
}

export type StoragePlanPayload = {
  quantity_kg: number
  current_price_per_quintal: number
  expected_future_price_per_quintal?: number | null
  storage_days: number
  storage_cost_per_quintal_day: number
  handling_cost_per_quintal?: number
  transport_cost?: number
  expected_loss_percent?: number
  spoilage_percent?: number
}

export type StoragePlanResult = {
  quantity_kg?: number
  quantity_quintals?: number
  current_revenue?: number
  expected_future_revenue?: number
  storage_cost?: number
  handling_cost?: number
  transport_cost?: number
  spoilage_loss?: number
  total_cost?: number
  expected_profit?: number
  net_gain?: number
  roi?: number
  recommended_action?: string
  recommendation?: string
  profitable?: boolean
  break_even_price?: number
  explanation?: string[]
  warnings?: string[]
}

export type TransportPlanPayload = {
  quantity_kg: number
  distance_km: number
  cost_per_km_tonne: number
  loading_cost?: number
  unloading_cost?: number
  toll_cost?: number
  other_cost?: number
  vehicle_capacity_kg?: number
  number_of_trips?: number
}

export type TransportPlanResult = {
  quantity_kg?: number
  quantity_tonnes?: number
  distance_km?: number
  number_of_trips?: number
  transport_cost?: number
  loading_cost?: number
  unloading_cost?: number
  toll_cost?: number
  other_cost?: number
  total_cost?: number
  cost_per_kg?: number
  cost_per_quintal?: number
  recommended_vehicle?: string
  recommended_action?: string
  recommendation?: string
  explanation?: string[]
  warnings?: string[]
}

export type BatchImage = {
  id: number
  file_name: string
  mime_type: string
  image_url: string | null
  annotated_url: string | null
  analysis_json: Record<string, unknown> | null
}

export type QualityAssessment = {
  quality_score: number
  quality_grade: string
  commercial_class: string
  rejection_probability: number
  size_uniformity: number
  bruise_severity: number
  crack_severity: number
  scab_severity: number
  discoloration_severity: number
  deformity_severity: number
  sprout_severity: number
  surface_defect_severity: number
  confidence: number
  model_mode: string
  feature_summary: Record<string, unknown>
}

export type Alternative = {
  action: string
  title: string
  market: string
  timing: string
  selling_price: number
  gross_revenue: number
  net_profit: number
  roi: number
  risk_score: number
  confidence: number
  costs: Record<string, number>
  reasons: string[]
}

export type Recommendation = {
  recommended_action: string
  recommended_market: string
  recommended_timing: string
  expected_selling_price: number
  expected_gross_revenue: number
  expected_net_profit: number
  expected_roi: number
  risk_score: number
  confidence: number
  alternatives: Alternative[]
  explanation: string[]
  cost_breakdown: Record<string, number>
  decision_factors: Array<{
    factor: string
    value: string | number
    contribution: number
    direction: 'positive' | 'negative'
    explanation: string
  }>
}

export type Batch = {
  id: number
  batch_code: string
  variety: string
  quantity_kg: number
  farmer_name: string | null
  source_location: string
  state: string
  district: string | null
  harvest_date: string | null
  intended_market: string | null
  status: string
  created_at: string
  updated_at: string
  images: BatchImage[]
  assessment: QualityAssessment | null
  recommendation: Recommendation | null
  analysis_warnings?: string[]
}

export type BatchListItem = {
  id: number
  batch_code: string
  variety: string
  quantity_kg: number
  source_location: string
  status: string
  created_at: string
  grade: string | null
  quality_score: number | null
  action: string | null
  expected_net_profit: number | null
}

export type DashboardSummary = {
  total_batches: number
  analyzed_batches: number
  average_quality_score: number
  projected_value: number
  latest_modal_price: number
  price_change_percent: number
  recent_batches: BatchListItem[]
  price_forecast: ForecastPoint[]
  grade_distribution: Record<string, number>
  action_distribution: Record<string, number>
}

export type ModelStatusResponse = {
  runtime_mode: string
  models: Array<{
    name: string
    role: string
    configured: boolean
    loaded: boolean
    path: string | null
    note: string
  }>
  fallback: {
    name: string
    active: boolean
    features: string[]
  }
}

export type MarketSyncResponse = {
  state: string | null
  received: number
  inserted: number
  updated: number
  mandi_count: number
  live_data: boolean
  source: string
  note: string
}
