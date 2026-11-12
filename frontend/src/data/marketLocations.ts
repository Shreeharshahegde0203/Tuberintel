export type MarketLocation = {
  state: string
  district: string
  market: string
}

// Coordinates are used only by the weather card. Mandi/APMC options are never
// sourced from this file; they come from the backend database directory.
export const MARKET_COORDINATES: Record<string, { latitude: number; longitude: number }> = {
  'Karnataka::Bengaluru': { latitude: 12.9716, longitude: 77.5946 },
  'Karnataka::Bagrepalli': { latitude: 13.7824, longitude: 77.7953 },
  'Karnataka::Belagavi': { latitude: 15.8497, longitude: 74.4977 },
  'Karnataka::Chikkaballapur': { latitude: 13.4355, longitude: 77.7315 },
  'Karnataka::Dharwad': { latitude: 15.4589, longitude: 75.0078 },
  'Karnataka::Hassan': { latitude: 13.0033, longitude: 76.1004 },
  'Karnataka::Kolar': { latitude: 13.1362, longitude: 78.1291 },
  'Uttar Pradesh::Agra': { latitude: 27.1767, longitude: 78.0081 },
  'Uttar Pradesh::Aligarh': { latitude: 27.8974, longitude: 78.088 },
  'Uttar Pradesh::Farrukhabad': { latitude: 27.39, longitude: 79.58 },
  'Uttar Pradesh::Kanpur': { latitude: 26.4499, longitude: 80.3319 },
  'Uttar Pradesh::Meerut': { latitude: 28.9845, longitude: 77.7064 },
  'Gujarat::Ahmedabad': { latitude: 23.0225, longitude: 72.5714 },
  'Gujarat::Banaskantha': { latitude: 24.1724, longitude: 72.4346 },
  'Gujarat::Deesa': { latitude: 24.2585, longitude: 72.1907 },
  'Gujarat::Gandhinagar': { latitude: 23.2156, longitude: 72.6369 },
  'Gujarat::Rajkot': { latitude: 22.3039, longitude: 70.8022 },
  'Madhya Pradesh::Bhopal': { latitude: 23.2599, longitude: 77.4126 },
  'Madhya Pradesh::Dewas': { latitude: 22.9676, longitude: 76.0534 },
  'Madhya Pradesh::Indore': { latitude: 22.7196, longitude: 75.8577 },
  'Madhya Pradesh::Ujjain': { latitude: 23.1765, longitude: 75.7885 },
  'Punjab::Amritsar': { latitude: 31.634, longitude: 74.8723 },
  'Punjab::Jalandhar': { latitude: 31.326, longitude: 75.5762 },
  'Punjab::Ludhiana': { latitude: 30.901, longitude: 75.8573 },
  'Punjab::Patiala': { latitude: 30.3398, longitude: 76.3869 },
  'West Bengal::Bardhaman': { latitude: 23.2324, longitude: 87.8615 },
  'West Bengal::Hooghly': { latitude: 22.8963, longitude: 88.2461 },
  'West Bengal::Kolkata': { latitude: 22.5726, longitude: 88.3639 },
  'Bihar::Nalanda': { latitude: 25.1365, longitude: 85.4437 },
  'Bihar::Patna': { latitude: 25.5941, longitude: 85.1376 },
  'Bihar::Vaishali': { latitude: 25.6838, longitude: 85.3554 },
}

export const DEFAULT_MARKET_LOCATION: MarketLocation = {
  state: 'Karnataka',
  district: 'Bengaluru',
  market: 'Bangalore APMC (published aggregate)',
}

const REMOVED_MARKETS = new Set([
  'Binny Mill (F&V), Bengaluru',
  'Bengaluru APMC',
])

export function readMarketLocation(): MarketLocation {
  const legacyState = localStorage.getItem('tuberintel-location')
  const legacyCity = localStorage.getItem('tuberintel-city')

  const storedState =
    localStorage.getItem('tuberintel-state') ||
    legacyState ||
    DEFAULT_MARKET_LOCATION.state

  const storedDistrict =
    localStorage.getItem('tuberintel-district') ||
    legacyCity ||
    DEFAULT_MARKET_LOCATION.district

  const storedMarket =
    localStorage.getItem('tuberintel-market') ||
    DEFAULT_MARKET_LOCATION.market

  if (storedState === DEFAULT_MARKET_LOCATION.state && REMOVED_MARKETS.has(storedMarket)) {
    const migrated = {
      ...DEFAULT_MARKET_LOCATION,
    }

    localStorage.setItem('tuberintel-state', migrated.state)
    localStorage.setItem('tuberintel-location', migrated.state)
    localStorage.setItem('tuberintel-district', migrated.district)
    localStorage.setItem('tuberintel-city', migrated.district)
    localStorage.setItem('tuberintel-market', migrated.market)

    return migrated
  }

  return {
    state: storedState,
    district: storedDistrict,
    market: storedState !== DEFAULT_MARKET_LOCATION.state && (REMOVED_MARKETS.has(storedMarket) || !localStorage.getItem('tuberintel-market')) ? '' : storedMarket,
  }
}

export function persistMarketLocation(location: MarketLocation) {
  localStorage.setItem('tuberintel-state', location.state)
  localStorage.setItem('tuberintel-location', location.state)
  localStorage.setItem('tuberintel-district', location.district)
  localStorage.setItem('tuberintel-city', location.district)
  localStorage.setItem('tuberintel-market', location.market)
  window.dispatchEvent(new CustomEvent<MarketLocation>('tuberintel-location', { detail: location }))
}

export function coordinatesFor(location: MarketLocation) {
  return MARKET_COORDINATES[`${location.state}::${location.district}`] || MARKET_COORDINATES['Karnataka::Bengaluru']
}
