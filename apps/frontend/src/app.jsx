import { lazy, Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import { LocaleProvider } from './LocaleContext'
import ErrorBoundary from './ui/ErrorBoundary'
import SideNavBar from './components/SideNavBar'
import './app.css'

// ── Lazy-loaded pages (code splitting) ───────────────────────
const UploadPage     = lazy(() => import('./pages/uploadpage'))
const WorkspacePage  = lazy(() => import('./pages/WorkspacePage'))
const HistoryPage    = lazy(() => import('./pages/historypage'))
const DashboardPage  = lazy(() => import('./pages/DashboardPage'))
const ChatPage       = lazy(() => import('./pages/ChatPage'))
const ProcessingPage = lazy(() => import('./pages/processingpage'))
const ResultsPage    = lazy(() => import('./pages/resultspage'))
const SummarizePage  = lazy(() => import('./pages/summarizepage'))

/** Page-level loading fallback */
function PageLoader() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      height: '100vh', flexDirection: 'column', gap: 16,
    }}>
      <span className="material-symbols-outlined spin" style={{
        fontSize: 36, color: 'var(--accent)',
        filter: 'drop-shadow(0 0 12px rgba(96,165,250,0.4))',
      }}>autorenew</span>
      <span style={{ fontSize: 13, color: 'var(--text-muted)', fontWeight: 500 }}>Loading...</span>
    </div>
  )
}

function App() {
  return (
    <ErrorBoundary>
      <LocaleProvider>
        <Router>
          <div className="app-layout">
            <SideNavBar />
            <main className="main-content">
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/" element={<UploadPage />} />
                  <Route path="/workspace/:id" element={<WorkspacePage />} />
                  <Route path="/workspace" element={<WorkspacePage />} />
                  <Route path="/processing/:id" element={<ProcessingPage />} />
                  <Route path="/results/:id" element={<ResultsPage />} />
                  <Route path="/summarize" element={<SummarizePage />} />
                  <Route path="/history" element={<HistoryPage />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  <Route path="/chat" element={<ChatPage />} />
                </Routes>
              </Suspense>
            </main>
          </div>
          <ToastContainer
            position="bottom-right"
            theme="dark"
            autoClose={4000}
            hideProgressBar={false}
            newestOnTop
            closeOnClick
            pauseOnFocusLoss={false}
          />
        </Router>
      </LocaleProvider>
    </ErrorBoundary>
  )
}

export default App
