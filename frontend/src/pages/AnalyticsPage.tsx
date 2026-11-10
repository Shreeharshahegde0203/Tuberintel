import { createPriceAnalyticsTranslator } from '../i18n/priceAnalyticsLabels'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CalendarDays,
  Gauge,
  Landmark,
  TrendingDown,
  TrendingUp,
} from 'lucide-react'
import { useEffect, useState } from 'react'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'

import { ErrorState, LoadingState } from '../components/Common'
import { useI18n } from '../i18n/I18nContext'
import {
  getMarketAnalytics,
  getMarketFilters,
  getMarketForecast,
} from '../services/api'
import type { MarketForecastResponse } from '../services/api'
import { formatCurrency, formatNumber } from '../services/format'
import type { MarketAnalytics, MarketFilters } from '../types'


export default function AnalyticsPage() {
  const [state, setState] = useState(
    () => localStorage.getItem('tuberintel-location') || 'Karnataka'
  )

  const [district, setDistrict] = useState('')
  const [market, setMarket] = useState('')
  const [variety, setVariety] = useState('')
  const [windowDays, setWindowDays] = useState(90)

  const [data, setData] = useState<MarketAnalytics | null>(null)
  const [filters, setFilters] = useState<MarketFilters | null>(null)

  const [forecastData, setForecastData] =
    useState<MarketForecastResponse | null>(null)

  const [forecastLoading, setForecastLoading] = useState(false)

  const [error, setError] = useState('')

  const { language, locale, t: appT } = useI18n()
  // TUBERINTEL PRICE ANALYTICS LABELS V1
  const t = createPriceAnalyticsTranslator(language, appT)
  const load = async () => {
    setError('')

    try {
      const [analytics, filterData] = await Promise.all([
        getMarketAnalytics({
          state,
          district: district || undefined,
          market: market || undefined,
          variety: variety || undefined,
          window_days: windowDays,
        }),

        getMarketFilters(state),
      ])

      setData(analytics)
      setFilters(filterData)
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
        err?.message ||
        'Unable to load market analytics.'
      )
    }
  }


  const loadForecast = async () => {
    setForecastLoading(true)

    try {
      const response = await getMarketForecast({
        state,
        district: district || undefined,
        market: market || undefined,
        variety: variety || undefined,
        horizon_days: 30,
      })

      setForecastData(response)
    } catch {
      /*
       * Do not expose backend/network errors such as 502/503/504
       * to the farmer.
       *
       * Setting forecastData to null automatically activates the
       * analytics forecast already returned by /market/analytics.
       */
      setForecastData(null)
    } finally {
      setForecastLoading(false)
    }
  }


  useEffect(() => {
    load()
  }, [
    state,
    district,
    market,
    variety,
    windowDays,
  ])


  useEffect(() => {
    loadForecast()
  }, [
    state,
    district,
    market,
    variety,
  ])


  if (error) {
    return (
      <ErrorState
        message={String(error)}
        retry={load}
      />
    )
  }


  if (!data || !filters) {
    return <LoadingState />
  }


  const daily = data.daily_series.map((point) => ({
    ...point,
    label: new Date(point.date).toLocaleDateString(
      locale,
      {
        day: '2-digit',
        month: 'short',
      }
    ),
  }))


  /*
   * PRIMARY:
   * /market/forecast
   *
   * FALLBACK:
   * forecast already included inside /market/analytics
   */
  const primaryForecast = forecastData?.points ?? []

  const fallbackForecast = data.forecast ?? []

  const activeForecast =
    primaryForecast.length > 0
      ? primaryForecast
      : fallbackForecast


  const usingAnalyticsFallback =
    primaryForecast.length === 0 &&
    fallbackForecast.length > 0


  const forecastAvailable =
    activeForecast.length > 0


  const forecast = activeForecast.map((point) => ({
    ...point,

    label: new Date(point.date).toLocaleDateString(
      locale,
      {
        day: '2-digit',
        month: 'short',
      }
    ),
  }))


  const TrendIcon =
    data.change_percent_7d < 0
      ? TrendingDown
      : TrendingUp


  const findForecastPoint = (day: number) => {
    if (activeForecast.length === 0) {
      return null
    }

    /*
     * Dedicated prediction response contains horizon_days.
     * Existing analytics fallback may not.
     */
    if (forecastData) {
      const exact = forecastData.points.find(
        (point) => point.horizon_days === day
      )

      if (exact) {
        return exact
      }
    }

    const index = Math.min(
      day - 1,
      activeForecast.length - 1
    )

    return activeForecast[index] ?? null
  }


  const day1 = findForecastPoint(1)
  const day7 = findForecastPoint(7)
  const day14 = findForecastPoint(14)
  const day30 = findForecastPoint(30)


  const forecastBadge = () => {
    if (forecastLoading && !forecastAvailable) {
      return 'Updating forecast'
    }

    if (forecastData?.fallback_used) {
      return 'Fallback estimate · low confidence'
    }

    if (forecastData) {
      return `${forecastData.confidence} confidence`
    }

    if (usingAnalyticsFallback) {
      return 'Fallback estimate'
    }

    return 'Temporarily unavailable'
  }


  return (
    <>
      <section className="methodology-note-card">
        <div><CalendarDays size={21} /><div>
          <strong>Public webpage prices · latest report {data.daily_series.length ? data.daily_series[data.daily_series.length - 1].date : 'unavailable'}</strong>
          <p>Fetches online without an API key; supported web source: Bangalore APMC published aggregate.
            Refresh price data to fetch again. Missing reporting dates are not actual prices.
            Forecasts use available history; short-history ranges are uncalibrated estimates.</p>
        </div></div>
      </section>
      <section className="page-intro">
        <div>
          <span className="section-kicker">
            {t('analytics.eyebrow')}
          </span>

          <h1>
            {t('analytics.title')}
          </h1>

          <p>
            {t('analytics.description')}
          </p>
        </div>
      </section>


      <section className="analytics-filter-bar">
        <label>
          <span>{t('market.state')}</span>

          <select
            value={state}
            onChange={(e) => {
              setState(e.target.value)
              setDistrict('')
              setMarket('')
              setVariety('')

              localStorage.setItem(
                'tuberintel-location',
                e.target.value
              )
            }}
          >
            {filters.states.map((item) => (
              <option key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>


        <label>
          <span>{t('market.district')}</span>

          <select
            value={district}
            onChange={(e) => {
              setDistrict(e.target.value)
              setMarket('')
            }}
          >
            <option value="">
              {t('common.all')}
            </option>

            {filters.districts.map((item) => (
              <option key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>


        <label>
          <span>{t('market.market')}</span>

          <select
            value={market}
            onChange={(e) =>
              setMarket(e.target.value)
            }
          >
            <option value="">
              {t('common.all')}
            </option>

            {filters.markets.map((item) => (
              <option key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>


        <label>
          <span>{t('market.variety')}</span>

          <select
            value={variety}
            onChange={(e) =>
              setVariety(e.target.value)
            }
          >
            <option value="">
              {t('common.all')}
            </option>

            {filters.varieties.map((item) => (
              <option key={item}>
                {item}
              </option>
            ))}
          </select>
        </label>


        <label>
          <span>{t('analytics.window')}</span>

          <select
            value={windowDays}
            onChange={(e) =>
              setWindowDays(
                Number(e.target.value)
              )
            }
          >
            <option value={30}>
              30 {t('common.days')}
            </option>

            <option value={90}>
              90 {t('common.days')}
            </option>

            <option value={180}>
              180 {t('common.days')}
            </option>

            <option value={365}>
              1 {t('common.year')}
            </option>
          </select>
        </label>
      </section>


      <section className="analytics-stat-grid">
        <article>
          <span>
            <Landmark size={21} />
          </span>

          <div>
            <small>
              {'Latest reported average'}
            </small>

            <strong>
              {formatCurrency(
                data.current_average,
                0,
                language
              )}
            </strong>

            <em>
              / {t('common.quintal')}
            </em>
          </div>
        </article>


        <article>
          <span>
            <TrendIcon size={21} />
          </span>

          <div>
            <small>
              {'Change over last 7 observations'}
            </small>

            <strong
              className={
                data.change_percent_7d < 0
                  ? 'negative-text'
                  : 'positive-text'
              }
            >
              {data.change_percent_7d >= 0
                ? '+'
                : ''}

              {data.change_percent_7d.toFixed(1)}%
            </strong>

            <em>
              {'Last 30 observations'}:{' '}

              {data.change_percent_30d >= 0
                ? '+'
                : ''}

              {data.change_percent_30d.toFixed(1)}%
            </em>
          </div>
        </article>


        <article>
          <span>
            <Activity size={21} />
          </span>

          <div>
            <small>
              {t('analytics.volatility')}
            </small>

            <strong>
              {data.volatility_percent.toFixed(1)}%
            </strong>

            <em>
              {t('analytics.priceRange')}:{' '}

              {formatCurrency(
                data.price_range,
                0,
                language
              )}
            </em>
          </div>
        </article>


        <article>
          <span>
            <Gauge size={21} />
          </span>

          <div>
            <small>
              {t('analytics.confidence')}
            </small>

            <strong>
              {t(`analytics.${data.confidence}`)}
            </strong>

            <em>
              {formatNumber(
                data.data_points,
                0,
                language
              )}{' '}

              {t('analytics.observations')}
            </em>
          </div>
        </article>
      </section>


      <section className="analytics-main-grid">
        <article className="market-panel historical-chart-card">
          <div className="market-panel-head">
            <div>
              <span className="section-kicker">
                {t('analytics.history')}
              </span>

              <h2>
                {t('analytics.priceHistory')}
              </h2>
            </div>

            <span className="data-chip">
              <CalendarDays size={15} />

              {data.window_days}{' '}
              {t('common.days')}
            </span>
          </div>


          <div className="analytics-chart">
            <ResponsiveContainer
              width="100%"
              height="100%"
            >
              <LineChart
                data={daily}
                margin={{
                  top: 12,
                  right: 18,
                  left: -8,
                  bottom: 0,
                }}
              >
                <CartesianGrid
                  vertical={false}
                  strokeDasharray="3 3"
                />

                <XAxis
                  dataKey="label"
                  axisLine={false}
                  tickLine={false}
                  minTickGap={24}
                />

                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(value) =>
                    `₹${Math.round(Number(value))}`
                  }
                />

                <Tooltip
                  formatter={(value, name) => [
                    formatCurrency(
                      Number(value),
                      0,
                      language
                    ),
                    String(name),
                  ]}
                />

                <Legend />

                <Line
                  type="monotone"
                  dataKey="average_modal_price"
                  name={t('analytics.dailyAverage')}
                  stroke="var(--market-green-dark)"
                  strokeWidth={2.3}
                  dot={false}
                />

                <Line
                  type="monotone"
                  dataKey="moving_average_7d"
                  name={'7-observation moving average'}
                  stroke="#d18a35"
                  strokeWidth={2}
                  dot={false}
                />

                <Line
                  type="monotone"
                  dataKey="moving_average_30d"
                  name={'30-observation moving average'}
                  stroke="#5e78a4"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </article>


        <article className="market-panel analytics-insight-card">
          <div className="market-panel-head">
            <div>
              <span className="section-kicker">
                {t('analytics.marketSignal')}
              </span>

              <h2>
                {t('analytics.keyFindings')}
              </h2>
            </div>
          </div>


          <div className="insight-list">
            <div>
              <span>
                <Landmark size={19} />
              </span>

              <div>
                <small>
                  {t('analytics.bestMarket')}
                </small>

                <strong>
                  {data.best_market}
                </strong>
              </div>
            </div>


            <div>
              <span>
                <BarChart3 size={19} />
              </span>

              <div>
                <small>
                  {t('analytics.strongestVariety')}
                </small>

                <strong>
                  {data.strongest_variety}
                </strong>
              </div>
            </div>


            <div>
              <span>
                <Activity size={19} />
              </span>

              <div>
                <small>
                  {t('analytics.coverage')}
                </small>

                <strong>
                  {data.market_count}{' '}
                  {t('analytics.markets')}
                </strong>
              </div>
            </div>


            <div>
              <span>
                <AlertTriangle size={19} />
              </span>

              <div>
                <small>
                  {t('analytics.riskRead')}
                </small>

                <strong>
                  {data.volatility_percent > 8
                    ? t('analytics.highVariation')
                    : t('analytics.normalVariation')}
                </strong>
              </div>
            </div>
          </div>
        </article>
      </section>


      <section className="market-panel forecast-card">
        <div className="market-panel-head">
          <div>
            <span className="section-kicker">
              PRICE OUTLOOK
            </span>

            <h2>
              30-day potato price outlook
            </h2>

            {forecastData && (
              <p>
                {forecastData.model_name}
                {' · '}
                {forecastData.model_version}
                {' · '}
                {forecastData.training_points}{' '}
                training observations
              </p>
            )}

            {usingAnalyticsFallback && (
              <p>
                Using the latest stored market history
                while the advanced forecast service is
                temporarily unavailable.
              </p>
            )}
          </div>


          <span className="forecast-badge">
            {forecastBadge()}
          </span>
        </div>


        {forecastLoading && !forecastAvailable && (
          <div style={{ padding: '24px 0' }}>
            <LoadingState />
          </div>
        )}


        {!forecastLoading && !forecastAvailable && (
          <div className="methodology-note-card">
            <div>
              <AlertTriangle size={21} />

              <div>
                <strong>
                  Prediction temporarily unavailable
                </strong>

                <p>
                  There is not enough stored market
                  history to produce a reliable
                  estimate right now.
                </p>
              </div>
            </div>
          </div>
        )}


        {forecastAvailable && (
          <>
            <section
              className="analytics-stat-grid"
              style={{
                marginTop: '18px',
                marginBottom: '22px',
              }}
            >
              {[
                { day: 1, point: day1 },
                { day: 7, point: day7 },
                { day: 14, point: day14 },
                { day: 30, point: day30 },
              ].map(({ day, point }) => (
                <article key={day}>
                  <span>
                    <TrendingUp size={21} />
                  </span>

                  <div>
                    <small>
                      Day +{day}
                    </small>

                    <strong>
                      {point
                        ? formatCurrency(
                            point.predicted_price,
                            0,
                            language
                          )
                        : '—'}
                    </strong>

                    <em>
                      {point
                        ? `${formatCurrency(
                            point.lower_bound,
                            0,
                            language
                          )} – ${formatCurrency(
                            point.upper_bound,
                            0,
                            language
                          )}`
                        : 'Estimate unavailable'}
                    </em>
                  </div>
                </article>
              ))}
            </section>


            <div className="analytics-chart forecast-chart">
              <ResponsiveContainer
                width="100%"
                height="100%"
              >
                <LineChart
                  data={forecast}
                  margin={{
                    top: 12,
                    right: 18,
                    left: -8,
                    bottom: 0,
                  }}
                >
                  <CartesianGrid
                    vertical={false}
                    stroke="#e5e9e5"
                  />

                  <XAxis
                    dataKey="label"
                    axisLine={false}
                    tickLine={false}
                    minTickGap={24}
                  />

                  <YAxis
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(value) =>
                      `₹${Math.round(Number(value))}`
                    }
                  />

                  <Tooltip
                    formatter={(value, name) => [
                      formatCurrency(
                        Number(value),
                        0,
                        language
                      ),
                      String(name),
                    ]}
                  />

                  <Legend />

                  <Line
                    type="monotone"
                    dataKey="upper_bound"
                    name={'Upper estimate'}
                    stroke="#8a938d"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    dot={false}
                  />

                  <Line
                    type="monotone"
                    dataKey="predicted_price"
                    name={t('analytics.predictedPrice')}
                    stroke="#176b45"
                    strokeWidth={2.5}
                    dot={false}
                  />

                  <Line
                    type="monotone"
                    dataKey="lower_bound"
                    name={'Lower estimate'}
                    stroke="#8a938d"
                    strokeWidth={1}
                    strokeDasharray="4 4"
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>


            <div
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '10px',
                marginTop: '18px',
              }}
            >
              {forecastData ? (
                <>
                  <span className="data-chip">
                    Model: {forecastData.model_name}
                  </span>

                  <span className="data-chip">
                    Confidence:{' '}
                    {forecastData.confidence}
                  </span>

                  <span className="data-chip">
                    Training points:{' '}
                    {forecastData.training_points}
                  </span>

                  <span className="data-chip">
                    {forecastData.fallback_used
                      ? 'Statistical fallback active'
                      : 'Validated forecasting model'}
                  </span>
                </>
              ) : (
                <span className="data-chip">
                  Stored-data fallback active
                </span>
              )}
            </div>
          </>
        )}
      </section>


      <section className="market-panel ranking-table-card">
        <div className="market-panel-head">
          <div>
            <span className="section-kicker">
              {t('analytics.comparison')}
            </span>

            <h2>
              {t('analytics.marketRanking')}
            </h2>
          </div>
        </div>


        <div className="responsive-table">
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>{t('market.market')}</th>
                <th>{t('market.district')}</th>
                <th>{t('market.variety')}</th>
                <th>{t('market.min')}</th>
                <th>{t('market.modal')}</th>
                <th>{t('market.max')}</th>
                <th>{t('market.spread')}</th>
              </tr>
            </thead>

            <tbody>
              {data.rankings.map((row) => (
                <tr
                  key={`${row.rank}-${row.market}-${row.variety}`}
                >
                  <td>
                    <span className="rank-number">
                      {row.rank}
                    </span>
                  </td>

                  <td>
                    <strong>
                      {row.market}
                    </strong>
                  </td>

                  <td>
                    {row.district}
                  </td>

                  <td>
                    {row.variety}
                  </td>

                  <td>
                    {formatCurrency(
                      row.minimum_price,
                      0,
                      language
                    )}
                  </td>

                  <td>
                    <strong className="modal-price-cell">
                      {formatCurrency(
                        row.modal_price,
                        0,
                        language
                      )}
                    </strong>
                  </td>

                  <td>
                    {formatCurrency(
                      row.maximum_price,
                      0,
                      language
                    )}
                  </td>

                  <td>
                    {formatCurrency(
                      row.price_spread,
                      0,
                      language
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>


      <section className="methodology-note-card">
        <div>
          <AlertTriangle size={21} />

          <div>
            <strong>
              {t('analytics.methodology')}
            </strong>

            <p>
              {t('analytics.methodologyIntro')}
            </p>
          </div>
        </div>

        <ol>
          {data.methodology.map((item, index) => (
            <li key={item}>
              <span>
                {index + 1}
              </span>

              {item}
            </li>
          ))}
        </ol>
      </section>
    </>
  )
}