import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute } from './auth/ProtectedRoute'
import { AppShell } from './components/AppShell'
import { ErrorBoundary } from './components/ErrorBoundary'
import { LoadingState } from './components/Common'

const BatchResultPage = lazy(() => import('./pages/BatchResultPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const HistoryPage = lazy(() => import('./pages/HistoryPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const MarketPage = lazy(() => import('./pages/MarketPage'))
const ModelsPage = lazy(() => import('./pages/ModelsPage'))
const NewAnalysisPage = lazy(() => import('./pages/NewAnalysisPage'))

export default function App() {
  return (
    <Suspense fallback={<LoadingState label="Loading TuberIntel" />}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route element={<ProtectedRoute />}>
          <Route element={<AppShell />}>
            <Route index element={<RouteView title="Overview"><DashboardPage /></RouteView>} />
            <Route path="analyze" element={<RouteView title="Quality Check"><NewAnalysisPage /></RouteView>} />
            <Route path="market" element={<RouteView title="Mandi Prices"><MarketPage /></RouteView>} />
            <Route path="history" element={<RouteView title="Batch History"><HistoryPage /></RouteView>} />
            <Route path="models" element={<RouteView title="Models & Methods"><ModelsPage /></RouteView>} />
            <Route path="batches/:batchId" element={<RouteView title="Batch Result"><BatchResultPage /></RouteView>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Route>
      </Routes>
    </Suspense>
  )
}

function RouteView({ children, title }: { children: ReactNode; title: string }) {
  return <ErrorBoundary title={title}>{children}</ErrorBoundary>
}
