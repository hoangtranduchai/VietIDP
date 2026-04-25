import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ToastContainer } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'
import SideNavBar from './components/SideNavBar'
import UploadPage from './pages/uploadpage'
import WorkspacePage from './pages/WorkspacePage'
import HistoryPage from './pages/historypage'
import DashboardPage from './pages/DashboardPage'
import ChatPage from './pages/ChatPage'
import './app.css'

function App() {
  return (
    <Router>
      <div className="app-layout">
        <SideNavBar />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<UploadPage />} />
            <Route path="/workspace/:id" element={<WorkspacePage />} />
            <Route path="/workspace" element={<WorkspacePage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/chat" element={<ChatPage />} />
          </Routes>
        </main>
      </div>
      <ToastContainer position="bottom-right" theme="dark" />
    </Router>
  )
}

export default App
