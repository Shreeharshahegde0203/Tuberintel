import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './components/AppShell'
import { LoadingState } from './components/Common'

const AnalyticsPage = lazy(() => import('./pages/AnalyticsPage'))
const BatchResultPage = lazy(() => import('./pages/BatchResultPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const HistoryPage = lazy(() => import('./pages/HistoryPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const MarketPage = lazy(() => import('./pages/MarketPage'))
const ModelsPage = lazy(() => import('./pages/ModelsPage'))
const MarketplacePage = lazy(() => import('./pages/MarketplacePage'))
const NewAnalysisPage = lazy(() => import('./pages/NewAnalysisPage'))
const NewsPage = lazy(() => import('./pages/NewsPage'))

export default function App() {
  return (
    <Suspense fallback={<LoadingState label="Loading TuberIntel" />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route index element={<DashboardPage />} />
            <Route path="analyze" element={<NewAnalysisPage />} />
            <Route path="market" element={<MarketPage />} />
            <Route path="trade" element={<MarketplacePage />} />
            <Route path="analytics" element={<AnalyticsPage />} />
            <Route path="news" element={<NewsPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="models" element={<ModelsPage />} />
            <Route path="batches/:batchId" element={<BatchResultPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  )
}
