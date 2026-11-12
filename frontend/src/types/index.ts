export type ForecastPoint = {
  date: string
  predicted_price: number
  lower_bound: number
  upper_bound: number
}

export type DailyPricePoint = {
  date: string
  average_modal_price: number
  minimum_price: number
  maximum_price: number
  market_count: number
  moving_average_7d: number | null
  moving_average_30d: number | null
}

export type MarketPrice = {
  id?: number | null
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
}

export type MarketRank = {
  rank: number
  state: string
  district: string
  market: string
  variety: string
  modal_price: number
  minimum_price: number
  maximum_price: number
  price_spread: number
  arrival_date: string
}

export type ConsolidatedMarketReport = {
  state: string | null
  district: string | null
  date: string | null
  active_mandis: number
  records: number
  average_modal_price: number
  median_modal_price: number
  minimum_price: number
  maximum_price: number
  average_spread: number
  change_percent_7d: number
  direction: 'rising' | 'falling' | 'stable'
  source_note: string
  freshness: string
  arrival_volume_available: boolean
  arrival_volume_note: string
}

export type MarketStateOption = {
  code: string
  name: string
  type: 'State' | 'Union Territory' | string
  mandi_count: number
}

export type MandiDirectoryItem = {
  id: number
  state: string
  district: string
  market: string
  source: string
  is_enam: boolean | null
  last_seen_at: string
}

export type MandiDirectoryResponse = {
  state: string
  districts: string[]
  mandis: MandiDirectoryItem[]
  count: number
  source: string
  last_synced_at: string | null
  api_configured: boolean
}

export type MarketFilters = {
  states: string[]
  districts: string[]
  markets: string[]
  varieties: string[]
  grades: string[]
  latest_date: string | null
}

export type MarketOverview = {
  latest_prices: MarketPrice[]
  forecast: ForecastPoint[]
  price_direction: 'rising' | 'falling' | 'stable'
  change_percent: number
  best_market: string
  source_note: string
  freshness: string
  consolidated: ConsolidatedMarketReport
  top_markets: MarketRank[]
  states: string[]
  live_data: boolean
  last_sync: {
    id: number
    source: string
    resource_id: string
    state: string | null
    status: string
    records_received: number
    records_inserted: number
    records_updated: number
    error: string | null
    started_at: string
    finished_at: string | null
  } | null
}

export type MarketAnalytics = {
  state: string
  district: string | null
  market: string | null
  variety: string | null
  window_days: number
  daily_series: DailyPricePoint[]
  rankings: MarketRank[]
  forecast: ForecastPoint[]
  current_average: number
  change_percent_7d: number
  change_percent_30d: number
  volatility_percent: number
  price_range: number
  best_market: string
  strongest_variety: string
  data_points: number
  market_count: number
  confidence: 'low' | 'medium' | 'high'
  methodology: string[]
}

export type NewsArticle = {
  id: number
  source: string
  title: string
  summary: string
  url: string
  image_url: string | null
  category: string
  language: string
  published_at: string | null
  fetched_at: string
}

export type NewsResponse = {
  articles: NewsArticle[]
  categories: string[]
  sources: string[]
  freshness: string
  live_data: boolean
  note: string
}

export type WeatherResponse = {
  latitude: number
  longitude: number
  timezone: string
  current_temperature: number | null
  current_humidity: number | null
  current_wind_speed: number | null
  current_weather_code: number | null
  daily: Array<{
    date: string
    weather_code: number
    minimum_temperature: number
    maximum_temperature: number
    precipitation_probability: number
    precipitation_mm: number
  }>
  fetched_at: string
  source: string
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
  feature_summary: {
    images_analyzed?: number
    independent_images?: number
    duplicate_images_ignored?: number
    duplicate_sets?: Array<{
      sha256_prefix: string
      copies: number
    }>
    potatoes_detected?: number
    average_image_quality?: number
    quality_score_stddev?: number
    quality_score_range?: number
    aggregation_method?: string
    manual_review_required?: boolean
    review_reasons?: string[]
    vision_v1_images?: number
    model_artifacts?: Record<string, {
      stage?: string
      architecture?: string
      artifact?: string
      format?: string
      size_bytes?: number
      sha256?: string
      artifact_id?: string
    }>
    condition_distribution?: Record<string, number>
    top_condition?: string | null
    defect_area_percent?: Record<string, number>
    explainability_mode?: string
    [key: string]: unknown
  }
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
  eligible?: boolean
  assumption_status?: string
  price_source?: string
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

export type StoragePlanPayload = {
  quantity_kg: number
  current_price_per_quintal: number
  expected_price_per_quintal: number
  storage_days: number
  storage_cost_per_quintal_day: number
  expected_loss_percent: number
  handling_cost_per_quintal: number
}

export type StoragePlanResult = {
  sell_now_revenue: number
  stored_sale_revenue: number
  storage_cost: number
  handling_cost: number
  expected_loss_value: number
  net_storage_value: number
  advantage_over_sell_now: number
  recommendation: 'STORE' | 'SELL_NOW'
  break_even_price_per_quintal: number
}

export type TransportPlanPayload = {
  quantity_kg: number
  distance_km: number
  rate_per_km_tonne: number
  loading_cost: number
  unloading_cost: number
  tolls_and_other: number
}

export type TransportPlanResult = {
  tonnes: number
  linehaul_cost: number
  loading_cost: number
  unloading_cost: number
  tolls_and_other: number
  total_cost: number
  cost_per_quintal: number
}

export type TradeListing = {
  id: number
  listing_code: string
  listing_type: 'BUY' | 'SELL'
  owner_name: string
  contact_phone: string | null
  variety: string
  quantity_kg: number
  price_per_quintal: number
  state: string
  district: string
  location: string
  notes: string | null
  status: 'ACTIVE' | 'CLOSED' | string
  source_batch_id: number | null
  quality_grade: string | null
  quality_score: number | null
  size_class: string | null
  verified_quality: boolean
  created_at: string
  updated_at: string
  is_favorite: boolean
  is_owner: boolean
  is_demo: boolean
}

export type TradeListingPage = {
  items: TradeListing[]
  next_cursor: string | null
  total_returned: number
}

export type MarketplaceSummary = {
  active_buy_posts: number
  active_sell_posts: number
  verified_quality_posts: number
  varieties: string[]
  states: string[]
}

export type TradeListingCreate = {
  listing_type: 'BUY' | 'SELL'
  owner_name: string
  contact_phone?: string | null
  variety: string
  quantity_kg: number
  price_per_quintal: number
  state: string
  district: string
  location: string
  notes?: string | null
  source_batch_id?: number | null
  size_class?: string | null
}

export type ColdStorageFacility = {
  id: number
  name: string
  state: string
  district: string
  location: string
  total_capacity_tonnes: number
  available_capacity_tonnes: number
  estimated_cost_per_quintal_day: number
  phone: string | null
  source: string
  verified: boolean
}

export type TransportProvider = {
  id: number
  name: string
  state: string
  district: string
  base_location: string
  vehicle_types: string[]
  rate_per_km_tonne: number
  phone: string | null
  source: string
  verified: boolean
}

export type AssistantReply = {
  answer: string
  mode: 'local_grounded' | 'openai_grounded'
  sources: Array<{ title: string; kind: string; detail: string }>
  suggestions: string[]
  disclaimer: string
}
