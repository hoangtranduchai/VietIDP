import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import { useDocuments } from '../hooks/useDocuments'
import { useApi } from '../hooks/useApi'
import { healthCheck } from '../services/api'
import TopBar from '../layouts/TopBar'
import Skeleton from '../ui/Skeleton'
import StatusDot from '../ui/StatusDot'
import { MOCK_DOCUMENTS, MOCK_HEALTH, MOCK_BENCHMARK } from '../data/mockData'

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
            background: d.active ? 'linear-gradient(180deg, var(--accent), var(--accent-cyan))' : 'var(--accent-muted)',
            transition: 'height 0.5s var(--ease)',
            boxShadow: d.active ? '0 0 8px rgba(96,165,250,0.3)' : 'none',
          }} />
          <span style={{ fontSize: 9, color: 'var(--text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '100%', padding: '0 2px' }}>{d.label}</span>
        </div>
      ))}
    </div>
  )
}

function SystemRow({ label, status, detail, loading: isLoading }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--border)' }}>
      <span style={{ fontSize: 14, color: 'var(--text-primary)', fontWeight: 500 }}>{label}</span>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>{detail}</span>
        {isLoading ? (
          <Skeleton width={60} height={20} />
        ) : (
          <span className={`status-badge ${status === 'active' ? 'completed' : status === 'inactive' ? 'failed' : 'pending'}`}>
            <StatusDot status={status} size={6} /> {status}
          </span>
        )}
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { t, locale } = useLocale()
  const navigate = useNavigate()
  const { documents: realDocs, loading: docsLoading, error: docsError } = useDocuments(100)
  const healthApi = useApi(healthCheck)

  // Use mock data when backend unavailable
  const documents = (!docsLoading && (docsError || realDocs.length === 0)) ? MOCK_DOCUMENTS : realDocs
  const isMock = documents === MOCK_DOCUMENTS

  useEffect(() => {
    healthApi.execute()
    const interval = setInterval(() => { healthApi.execute() }, 30000)
    return () => clearInterval(interval)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const healthData = healthApi.data || (isMock ? MOCK_HEALTH : null)
  const sys = healthData?.services || {}

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

  // Benchmark mini summary
  const bench = MOCK_BENCHMARK

  return (
    <>
      <TopBar />
      <div className="page-container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ marginBottom: 4 }}>{t('dashTitle')}</h1>
            {isMock && (
              <span className="badge badge-yellow" style={{ fontSize: 10 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 12 }}>info</span>
                Demo Mode
              </span>
            )}
          </div>
        </div>

        {/* Stats */}
        {docsLoading && !isMock ? (
          <div style={{ display: 'flex', gap: 14, marginBottom: 24 }}>
            {[1,2,3,4].map(i => <Skeleton key={i} variant="card" height={110} style={{ flex: 1 }} />)}
          </div>
        ) : (
          <div className="stagger stats-row">
            <StatCard icon="description" label={t('totalDocs')} value={documents.length} sub={t('allTime')} glowColor="#60a5fa" />
            <StatCard icon="check_circle" label={t('completed')} value={completed.length} sub={`${documents.length ? Math.round(completed.length / documents.length * 100) : 0}% ${t('successRate')}`} glowColor="#34d399" />
            <StatCard icon="error" label={t('failed')} value={failed.length} sub={t('needAttention')} glowColor="#f87171" />
            <StatCard icon="speed" label={t('avgTime')} value={`${avgTime}s`} sub={t('perDoc')} glowColor="#22d3ee" />
          </div>
        )}

        <div className="dash-grid">
          <div className="card card-glow">
            <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 16 }}>{t('weeklyAct')}</p>
            <MiniBar data={weeklyData} />
          </div>
          <div className="card card-glow">
            <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 16 }}>{t('docTypes')}</p>
            {documents.length > 0 ? (
              <MiniBar data={Object.entries(documents.reduce((acc, d) => { const tp = d.extraction?.loai_van_ban || 'Other'; acc[tp] = (acc[tp]||0)+1; return acc }, {})).map(([label, value]) => ({ label, value }))} />
            ) : <p style={{ color: 'var(--text-muted)', fontSize: 13, textAlign: 'center', padding: 20 }}>{t('noData')}</p>}
          </div>
        </div>

        {/* Benchmark Summary Card */}
        <div className="card card-glow" style={{ marginBottom: 20, cursor: 'pointer' }} onClick={() => navigate('/benchmark')}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 36, height: 36, borderRadius: 10, background: 'rgba(124, 58, 237, 0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <span className="material-symbols-outlined" style={{ fontSize: 20, color: '#a78bfa' }}>science</span>
              </div>
              <div>
                <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)' }}>
                  {locale === 'vi' ? 'Hiệu năng AI Pipeline' : 'AI Pipeline Performance'}
                </p>
                <p style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                  {bench.document_level.total_documents} {locale === 'vi' ? 'văn bản' : 'documents'} · {bench.metadata.gpu}
                </p>
              </div>
            </div>
            <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--text-muted)' }}>arrow_forward</span>
          </div>
          <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {[
              { label: 'Exact Match', value: `${Math.round(bench.macro_averages.exact_match * 100)}%`, color: '#3b82f6' },
              { label: 'Token F1', value: `${Math.round(bench.macro_averages.token_f1 * 100)}%`, color: '#34d399' },
              { label: 'Char Sim', value: `${Math.round(bench.macro_averages.char_similarity * 100)}%`, color: '#22d3ee' },
              { label: locale === 'vi' ? 'Hoàn hảo' : 'Perfect', value: `${bench.document_level.perfect_documents}/${bench.document_level.total_documents}`, color: '#fbbf24' },
            ].map(({ label, value, color }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <div style={{ width: 8, height: 8, borderRadius: '50%', background: color, boxShadow: `0 0 8px ${color}60` }} />
                <div>
                  <div style={{ fontSize: 18, fontWeight: 800, fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>{value}</div>
                  <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600 }}>{label}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System */}
        <div className="card">
          <p style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--text-muted)', marginBottom: 8 }}>{t('sysComponents')}</p>
          <SystemRow label="Ollama LLM Server" status={sys.ollama || (isMock ? 'active' : 'inactive')} detail={`Model: ${sys.model || 'qwen2.5:7b'}`} loading={healthApi.loading && !isMock} />
          <SystemRow label="PostgreSQL / SQLite" status={sys.database || (isMock ? 'active' : 'inactive')} detail="Document storage" loading={healthApi.loading && !isMock} />
          <SystemRow label="YOLO Stamp Detector" status={sys.yolo || 'standby'} detail="YOLOv8x best.pt" loading={false} />
          <SystemRow label="VietOCR Engine" status={sys.vietocr || 'standby'} detail="vgg_transformer" loading={false} />
          <SystemRow label={sys.gpu_name || 'NVIDIA RTX 5070'} status={sys.gpu || (isMock ? 'active' : 'standby')} detail={sys.gpu_vram || '8GB VRAM'} loading={false} />
        </div>
      </div>
    </>
  )
}
