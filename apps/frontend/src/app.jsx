import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import Sidebar from './components/Sidebar'
import UploadPage from './pages/UploadPage'
import ProcessingPage from './pages/ProcessingPage'
import ResultsPage from './pages/ResultsPage'
import HistoryPage from './pages/HistoryPage'
import SummarizePage from './pages/SummarizePage'
import './App.css'

function AppLayout() {
  const location = useLocation();
  const hideSidebar = location.pathname.startsWith('/results');

  return (
    <div className="app-layout">
      {!hideSidebar && <Sidebar />}
      <main className="main-content" style={hideSidebar ? { marginLeft: 0, width: '100%' } : {}}>
        <Routes>
          <Route path="/" element={<UploadPage />} />
          <Route path="/processing/:id" element={<ProcessingPage />} />
          <Route path="/results/:id" element={<ResultsPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/summarize" element={<SummarizePage />} />
        </Routes>
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AppLayout />
      <ToastContainer position="bottom-right" theme="dark" />
    </Router>
  )
}

export default App
