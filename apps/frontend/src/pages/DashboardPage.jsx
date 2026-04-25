import { useState, useEffect } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

function StatCard({ icon, label, value, sub, color }) {
  return (
    <div style={{
      background: 'white', borderRadius: 12, padding: '24px 20px',
      border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)',
      flex: '1 1 200px', minWidth: 200,
    }}>
      <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start'}}>
        <div>
          <p style={{fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--outline)', marginBottom: 8}}>{label}</p>
          <p style={{fontSize: 32, fontWeight: 700, fontFamily: 'Epilogue', color: 'var(--primary)', lineHeight: 1}}>{value}</p>
          {sub && <p style={{fontSize: 12, color: 'var(--outline)', marginTop: 4}}>{sub}</p>}
        </div>
        <div style={{
          width: 44, height: 44, borderRadius: 10,
          background: color || 'rgba(0,51,102,0.08)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <span className="material-symbols-outlined" style={{fontSize: 22, color: 'var(--primary-container)'}}>{icon}</span>
        </div>
      </div>
    </div>
  )
}

function MiniBar({ data, maxVal }) {
  const max = maxVal || Math.max(...data.map(d => d.value), 1)
  return (
    <div style={{display: 'flex', alignItems: 'flex-end', gap: 3, height: 80}}>
      {data.map((d, i) => (
        <div key={i} style={{flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4}}>
          <div style={{
            width: '100%', borderRadius: 3,
            height: Math.max(4, (d.value / max) * 70),
            background: d.color || 'var(--secondary-container)',
            transition: 'height 0.3s ease',
          }} />
          <span style={{fontSize: 9, color: 'var(--outline)'}}>{d.label}</span>
        </div>
      ))}
    </div>
  )
}

function SystemStatusRow({ label, status, detail }) {
  const colors = {
    active: { bg: '#f0fdf4', text: '#15803d', dot: '#22c55e' },
    inactive: { bg: '#fef2f2', text: '#dc2626', dot: '#ef4444' },
    standby: { bg: '#fefce8', text: '#ca8a04', dot: '#eab308' },
  }
  const c = colors[status] || colors.standby
  return (
    <div style={{
      display: 'flex', justifyContent: 'space-between', alignItems: 'center',
      padding: '12px 0', borderBottom: '1px solid var(--border-subtle)',
    }}>
      <span style={{fontSize: 14, color: 'var(--on-surface)', fontWeight: 500}}>{label}</span>
      <div style={{display: 'flex', alignItems: 'center', gap: 12}}>
        <span style={{fontSize: 12, color: 'var(--outline)'}}>{detail}</span>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 6,
          padding: '3px 10px', borderRadius: 999,
          background: c.bg, color: c.text, fontSize: 11, fontWeight: 600,
        }}>
          <span style={{width: 6, height: 6, borderRadius: '50%', background: c.dot}} />
          {status}
        </span>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const [stats, setStats] = useState({ total: 0, completed: 0, failed: 0, avgTime: 0 })
  const [docs, setDocs] = useState([])
  const [systemStatus, setSystemStatus] = useState({})

  useEffect(() => {
    loadStats()
    checkSystem()
  }, [])

  const loadStats = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/documents?limit=100`)
      const allDocs = res.data.documents || []
      const completed = allDocs.filter(d => d.status === 'completed')
      const failed = allDocs.filter(d => d.status === 'failed')

      const avgTime = completed.length > 0
        ? completed.reduce((sum, d) => sum + (d.extraction?.processing_time || 0), 0) / completed.length
        : 0

      setStats({
        total: allDocs.length,
        completed: completed.length,
        failed: failed.length,
        avgTime: avgTime.toFixed(1),
      })
      setDocs(allDocs)
    } catch (err) {
      console.error('Stats load error:', err)
    }
  }

  const checkSystem = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/health`)
      setSystemStatus(res.data.services || {})
    } catch {
      setSystemStatus({ ollama: 'inactive', database: 'inactive' })
    }
  }

  // Build weekly chart data from docs
  const weekDays = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
  const today = new Date().getDay()
  const weeklyData = weekDays.map((label, i) => {
    const dayDocs = docs.filter(d => {
      if (!d.created_at) return false
      return new Date(d.created_at).getDay() === ((i + 1) % 7)
    })
    return { label, value: dayDocs.length, color: i === ((today + 6) % 7) ? 'var(--primary-container)' : 'var(--secondary-container)' }
  })

  const typeData = (() => {
    const types = {}
    docs.forEach(d => {
      const t = d.extraction?.loai_van_ban || 'Khác'
      types[t] = (types[t] || 0) + 1
    })
    return Object.entries(types).map(([label, value]) => ({ label: label.substring(0, 6), value }))
  })()

  return (
    <>
      <header className="topbar">
        <h1 className="topbar-title">NeuralIDP Enterprise</h1>
        <div className="topbar-status">
          <span className="topbar-status-dot" />
          Local Node: Active
        </div>
      </header>

      <div className="page-container">
        <h1>System Dashboard</h1>

        {/* Stat Cards */}
        <div style={{display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap'}}>
          <StatCard icon="description" label="Total Documents" value={stats.total} sub="All time" />
          <StatCard icon="check_circle" label="Completed" value={stats.completed} sub={`${stats.total ? Math.round(stats.completed/stats.total*100) : 0}% success rate`} color="rgba(22,163,74,0.1)" />
          <StatCard icon="error" label="Failed" value={stats.failed} sub="Need attention" color="rgba(220,38,38,0.1)" />
          <StatCard icon="speed" label="Avg Processing" value={`${stats.avgTime}s`} sub="Per document" color="rgba(0,210,255,0.1)" />
        </div>

        <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24, marginBottom: 24}}>
          {/* Weekly Activity */}
          <div style={{background: 'white', borderRadius: 12, padding: 20, border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)'}}>
            <p style={{fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--outline)', marginBottom: 16}}>Weekly Activity</p>
            <MiniBar data={weeklyData} />
          </div>

          {/* Document Types */}
          <div style={{background: 'white', borderRadius: 12, padding: 20, border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)'}}>
            <p style={{fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--outline)', marginBottom: 16}}>Document Types</p>
            {typeData.length > 0 ? <MiniBar data={typeData} /> : (
              <p style={{color: 'var(--outline)', fontSize: 13, textAlign: 'center', padding: 20}}>No data yet</p>
            )}
          </div>
        </div>

        {/* System Status */}
        <div style={{background: 'white', borderRadius: 12, padding: 20, border: '1px solid var(--border-subtle)', boxShadow: 'var(--shadow-sm)'}}>
          <p style={{fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--outline)', marginBottom: 8}}>System Components</p>
          <SystemStatusRow label="Ollama LLM Server" status={systemStatus.ollama || 'inactive'} detail={`Model: ${systemStatus.model || 'qwen2.5:7b'}`} />
          <SystemStatusRow label="PostgreSQL / SQLite" status={systemStatus.database || 'inactive'} detail="Document storage" />
          <SystemStatusRow label="YOLO Stamp Detector" status="standby" detail="YOLOv8x best.pt" />
          <SystemStatusRow label="VietOCR Engine" status="standby" detail="vgg_transformer" />
          <SystemStatusRow label="Redis / Celery" status="standby" detail="Task queue (optional)" />
          <SystemStatusRow label="NVIDIA RTX 5070" status="active" detail="8GB VRAM" />
        </div>
      </div>
    </>
  )
}
