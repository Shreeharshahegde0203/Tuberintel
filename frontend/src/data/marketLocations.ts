export type MarketLocation = {
  state: string
  city: string
  market?: string
}

export const DEFAULT_MARKET_LOCATION: MarketLocation = {
  state: 'Karnataka',
  city: 'Bengaluru',
  market: '',
}

const MARKET_COORDINATES: Record<string, { latitude: number; longitude: number }> = {
  'Karnataka::Bengaluru': { latitude: 12.9716, longitude: 77.5946 },
  'Karnataka::Kolar': { latitude: 13.1362, longitude: 78.1291 },
  'Karnataka::Chikkaballapur': { latitude: 13.4355, longitude: 77.7315 },
  'Karnataka::Belagavi': { latitude: 15.8497, longitude: 74.4977 },
  'Karnataka::Hassan': { latitude: 13.0033, longitude: 76.1004 },
}

export function readMarketLocation(): MarketLocation {
  const state = localStorage.getItem('tuberintel-state') || DEFAULT_MARKET_LOCATION.state
  const city = localStorage.getItem('tuberintel-city') || DEFAULT_MARKET_LOCATION.city
  const market = localStorage.getItem('tuberintel-market') || ''
  return { state, city, market }
}

export function persistMarketLocation(location: MarketLocation) {
  localStorage.setItem('tuberintel-state', location.state)
  localStorage.setItem('tuberintel-city', location.city)
  localStorage.setItem('tuberintel-market', location.market || '')
  window.dispatchEvent(new CustomEvent<MarketLocation>('tuberintel-location', { detail: location }))
}

export function coordinatesFor(location: MarketLocation) {
  return (
    MARKET_COORDINATES[`${location.state}::${location.city}`] ||
    MARKET_COORDINATES[`${location.state}::${location.market || ''}`] ||
    MARKET_COORDINATES['Karnataka::Bengaluru']
  )
}
