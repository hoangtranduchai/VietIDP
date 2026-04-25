import { useState, useEffect } from 'react'
import { useLocale } from '../LocaleContext'
import { useDocuments } from '../hooks/useDocuments'
import { useApi } from '../hooks/useApi'
import { healthCheck } from '../services/api'
import TopBar from '../layouts/TopBar'
import Skeleton from '../ui/Skeleton'
import StatusDot from '../ui/StatusDot'

function StatCard({ icon, label, value, sub, glowColor }) {
  return (
    <div className="stat-card fade-in-up" style={{ '--glow': glowColor }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = glowColor; e.currentTarget.style.boxShadow = `0 0 25px ${glowColor}22` }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--glass-border)'; e.currentTarget.style.boxShadow = 'none' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <p className="stat-label">{label}</p>
          <p className="stat-value">{value}</p>
          {sub && <p className="stat-sub">{sub}</p>}
        </div>
        <div style={{ width: 42, height: 42, borderRadius: 10, background: `${glowColor}14`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <span className="material-symbols-outlined" style={{ fontSize: 22, color: glowColor }}>{icon}</span>
        </div>
      </div>
    </div>
  )
}

function MiniBar({ data }) {
  const max = Math.max(...data.map(d => d.value), 1)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 80 }}>
      {data.map((d, i) => (
        <div key={i} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <div style={{
            width: '100%', borderRadius: 3,
            height: Math.max(4, (d.value / max) * 70),
            background: d.active ? 'linear-gradient(180deg, var(--accent), var(--accent-cyan))' : 'rgba(96,165,250,0.2)',
            transition: 'height 0.5s var(--ease)',
            boxShadow: d.active ? '0 0 8px rgba(96,165,250,0.3)' : 'none',
          }} />
          <span style={{ fontSize: 9, color: 'var(--text-muted)' }}>{d.label}</span>
        </div>
      ))}
    </div>
  )
}

function SystemRow({ label, status, detail }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 500 }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{detail}</span>
        <span className={`status-badge ${status === 'active' ? 'completed' : status === 'inactive' ? 'failed' : 'pending'}`}>
          <StatusDot status={status} size={6} /> {status}
        </span>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { t } = useLocale()
  const { documents, loading: docsLoading } = useDocuments(100)
  const healthApi = useApi(healthCheck)

  useEffect(() => { healthApi.execute() }, [])

  const completed = documents.filter(d => d.status === 'completed')
  const failed = documents.filter(d => d.status === 'failed')
  const avgTime = completed.length > 0
    ? (completed.reduce((s, d) => s + (d.extraction?.processing_time || 0), 0) / completed.length).toFixed(1)
    : '0'

  const today = new Date().getDay()
  const weeklyData = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((label, i) => ({
    label,
    value: documents.filter(d => d.created_at && new Date(d.created_at).getDay() === ((i + 1) % 7)).length,
    active: i === ((today + 6) % 7),
  }))

  const sys = healthApi.data?.services || {}

  return (
    <>
      <TopBar />
      <div className="page-container">
        <h1>{t('dashTitle')}</h1>

        {/* Stats */}
        {docsLoading ? (
          <div style={{ display: 'flex', gap: 14, marginBottom: 24 }}>
            {[1,2,3,4].map(i => <Skeleton key={i} variant="card" height={110} style={{ flex: 1 }} />)}
          </div>
        ) : (
          <div className="stagger" style={{ display: 'flex', gap: 14, marginBottom: 24, flexWrap: 'wrap' }}>
            <StatCard icon="description" label={t('totalDocs')} value={documents.length} sub={t('allTime')} glowColor="#60a5fa" />
            <StatCard icon="check_circle" label={t('completed')} value={completed.length} sub={`${documents.length ? Math.round(completed.length / documents.length * 100) : 0}% ${t('successRate')}`} glowColor="#34d399" />
            <StatCard icon="error" label={t('failed')} value={failed.length} sub={t('needAttention')} glowColor="#f87171" />
            <StatCard icon="speed" label={t('avgTime')} value={`${avgTime}s`} sub={t('perDoc')} glowColor="#22d3ee" />
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, marginBottom: 24 }}>
          <div className="card card-glow">
            <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 16 }}>{t('weeklyAct')}</p>
            <MiniBar data={weeklyData} />
          </div>
          <div className="card card-glow">
            <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 16 }}>{t('docTypes')}</p>
            {documents.length > 0 ? (
              <MiniBar data={Object.entries(documents.reduce((acc, d) => { const t = d.extraction?.loai_van_ban || 'Other'; acc[t] = (acc[t]||0)+1; return acc }, {})).map(([label, value]) => ({ label: label.substring(0,6), value }))} />
            ) : <p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 20 }}>{t('noData')}</p>}
          </div>
        </div>

        {/* System */}
        <div className="card">
          <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 8 }}>{t('sysComponents')}</p>
          <SystemRow label="Ollama LLM Server" status={sys.ollama || 'inactive'} detail={`Model: ${sys.model || 'qwen2.5:7b'}`} />
          <SystemRow label="PostgreSQL / SQLite" status={sys.database || 'inactive'} detail="Document storage" />
          <SystemRow label="YOLO Stamp Detector" status="standby" detail="YOLOv8x best.pt" />
          <SystemRow label="VietOCR Engine" status="standby" detail="vgg_transformer" />
          <SystemRow label="NVIDIA RTX 5070" status="active" detail="8GB VRAM" />
        </div>
      </div>
    </>
  )
}
