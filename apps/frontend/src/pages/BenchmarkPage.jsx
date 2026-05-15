import { useLocale } from '../LocaleContext'
import TopBar from '../layouts/TopBar'
import { MOCK_BENCHMARK, MOCK_PROFILER } from '../data/mockData'

/* ── Gauge Chart (CSS-only) ─────────────────────────────────── */
function GaugeChart({ value, label, color = '#3b82f6', size = 140 }) {
  const pct = Math.round(value * 100)
  const angle = value * 270 // 270° max sweep
  const r = (size - 16) / 2
  const circumference = 2 * Math.PI * r * (270 / 360)
  const offset = circumference * (1 - value)

  return (
    <div className="gauge-chart" style={{ width: size, height: size, position: 'relative' }}>
      <svg viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(135deg)' }}>
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke="var(--border)" strokeWidth="10"
          strokeDasharray={`${circumference} ${2 * Math.PI * r - circumference}`}
          strokeLinecap="round"
        />
        <circle
          cx={size / 2} cy={size / 2} r={r}
          fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={`${circumference - offset} ${2 * Math.PI * r - (circumference - offset)}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 1.5s var(--ease)', filter: `drop-shadow(0 0 6px ${color}60)` }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', paddingTop: 8,
      }}>
        <span style={{ fontSize: size * 0.25, fontWeight: 800, fontFamily: 'var(--font-display)', color: 'var(--text-primary)' }}>
          {pct}%
        </span>
        <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          {label}
        </span>
      </div>
    </div>
  )
}

/* ── Horizontal Bar ────────────────────────────────────────── */
function HBar({ value, maxValue = 1, color, height = 8 }) {
  const pct = Math.min((value / maxValue) * 100, 100)
  return (
    <div style={{ height, borderRadius: height / 2, background: 'var(--bg-elevated)', overflow: 'hidden', flex: 1 }}>
      <div style={{
        height: '100%', width: `${pct}%`, borderRadius: height / 2,
        background: `linear-gradient(90deg, ${color}, ${color}cc)`,
        transition: 'width 1.2s var(--ease)',
        boxShadow: `0 0 8px ${color}40`,
      }} />
    </div>
  )
}

/* ── Stat Pill ────────────────────────────────────────────── */
function StatPill({ icon, label, value, color }) {
  return (
    <div className="bench-stat-pill">
      <div className="bench-stat-icon" style={{ background: `${color}14` }}>
        <span className="material-symbols-outlined" style={{ fontSize: 18, color }}>{icon}</span>
      </div>
      <div>
        <div className="bench-stat-value">{value}</div>
        <div className="bench-stat-label">{label}</div>
      </div>
    </div>
  )
}

/* ── Field Rating Badge ──────────────────────────────────── */
function RatingBadge({ em, t }) {
  const rating =
    em >= 0.80 ? { label: t('benchGood'), cls: 'badge-green' } :
    em >= 0.65 ? { label: t('benchFair'), cls: 'badge-blue' } :
    em >= 0.50 ? { label: t('benchAvg'), cls: 'badge-yellow' } :
    em >= 0.30 ? { label: t('benchWeak'), cls: 'badge-red' } :
    { label: t('benchVeryWeak'), cls: 'badge-red' }

  return <span className={`badge ${rating.cls}`}>{rating.label}</span>
}

/* ── Field Label Map ─────────────────────────────────────── */
const FIELD_LABELS = {
  loai_van_ban: { vi: 'Loại văn bản', en: 'Doc Type' },
  so_hieu: { vi: 'Số hiệu', en: 'Doc ID' },
  ngay_ban_hanh: { vi: 'Ngày ban hành', en: 'Issue Date' },
  co_quan_ban_hanh: { vi: 'Cơ quan ban hành', en: 'Issuing Authority' },
  trich_yeu: { vi: 'Trích yếu', en: 'Abstract' },
  nguoi_ky: { vi: 'Người ký', en: 'Signer' },
}

/* ── Main Page ───────────────────────────────────────────── */
export default function BenchmarkPage() {
  const { t, locale } = useLocale()
  const b = MOCK_BENCHMARK
  const p = MOCK_PROFILER

  const fields = Object.entries(b.field_level)
  const fieldColors = {
    loai_van_ban: '#34d399',
    so_hieu: '#f87171',
    ngay_ban_hanh: '#60a5fa',
    co_quan_ban_hanh: '#fbbf24',
    trich_yeu: '#f87171',
    nguoi_ky: '#f97316',
  }

  const formatTime = (s) => {
    if (s >= 3600) return `${(s / 3600).toFixed(1)}h`
    if (s >= 60) return `${(s / 60).toFixed(1)}m`
    return `${s.toFixed(1)}s`
  }

  return (
    <>
      <TopBar />
      <div className="page-container bench-page">

        {/* ── Header ─────────────────────────────────────── */}
        <div className="bench-header fade-in-up">
          <div>
            <h1 style={{ marginBottom: 6 }}>{t('benchTitle')}</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t('benchSub')}</p>
          </div>
          <div className="bench-header-badges">
            <span className="badge badge-blue">
              <span className="material-symbols-outlined" style={{ fontSize: 12 }}>memory</span>
              {b.metadata.gpu}
            </span>
            <span className="badge badge-purple">
              <span className="material-symbols-outlined" style={{ fontSize: 12 }}>psychology</span>
              {b.metadata.llm_model}
            </span>
            <span className="badge badge-cyan">v{b.metadata.pipeline.split('v')[1]}</span>
          </div>
        </div>

        {/* ── Gauges Row ─────────────────────────────────── */}
        <div className="bench-gauges stagger">
          <div className="card card-glow bench-gauge-card fade-in-up">
            <GaugeChart value={b.macro_averages.exact_match} label={t('benchOverallEM')} color="#3b82f6" size={150} />
          </div>
          <div className="card card-glow bench-gauge-card fade-in-up">
            <GaugeChart value={b.macro_averages.token_f1} label={t('benchTokenF1')} color="#34d399" size={150} />
          </div>
          <div className="card card-glow bench-gauge-card fade-in-up">
            <GaugeChart value={b.macro_averages.char_similarity} label={t('benchCharSim')} color="#22d3ee" size={150} />
          </div>
          <div className="card card-glow bench-gauge-card fade-in-up">
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: 48, fontWeight: 900, fontFamily: 'var(--font-display)', color: 'var(--accent-warning)', lineHeight: 1 }}>
                {b.document_level.perfect_documents}
              </div>
              <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-muted)', marginTop: 8, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                {t('benchPerfectDocs')}
              </div>
              <div style={{ fontSize: 24, fontWeight: 700, color: 'var(--text-secondary)', marginTop: 4 }}>
                / {b.document_level.total_documents}
              </div>
              <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>{t('benchTotalDocs')}</div>
            </div>
          </div>
        </div>

        {/* ── Field Performance Table ───────────────────── */}
        <div className="card fade-in-up" style={{ marginBottom: 20 }}>
          <div className="bench-section-header">
            <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--accent)' }}>leaderboard</span>
            <h2>{t('benchFieldPerf')}</h2>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="bench-table">
              <thead>
                <tr>
                  <th>{t('benchField')}</th>
                  <th style={{ textAlign: 'center' }}>{t('benchEM')}</th>
                  <th style={{ textAlign: 'center' }}>{t('benchF1')}</th>
                  <th style={{ textAlign: 'center' }}>{t('benchSim')}</th>
                  <th style={{ textAlign: 'center' }}>{t('benchCorrect')}</th>
                  <th style={{ textAlign: 'center' }}>{t('benchWrong')}</th>
                  <th style={{ textAlign: 'center' }}>{t('benchMissed')}</th>
                  <th>{t('benchRating')}</th>
                  <th style={{ minWidth: 120 }}></th>
                </tr>
              </thead>
              <tbody>
                {fields.map(([key, f]) => (
                  <tr key={key}>
                    <td>
                      <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {FIELD_LABELS[key]?.[locale] || key}
                      </span>
                      <br />
                      <code style={{ fontSize: 10, color: 'var(--text-muted)' }}>{key}</code>
                    </td>
                    <td style={{ textAlign: 'center', fontWeight: 700, fontFamily: 'var(--font-mono)', color: f.exact_match >= 0.7 ? 'var(--accent-success)' : f.exact_match >= 0.5 ? 'var(--accent-warning)' : 'var(--accent-error)' }}>
                      {Math.round(f.exact_match * 100)}%
                    </td>
                    <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{Math.round(f.token_f1 * 100)}%</td>
                    <td style={{ textAlign: 'center', fontFamily: 'var(--font-mono)' }}>{Math.round(f.char_sim * 100)}%</td>
                    <td style={{ textAlign: 'center', color: 'var(--accent-success)', fontWeight: 600 }}>{f.correct}</td>
                    <td style={{ textAlign: 'center', color: 'var(--accent-error)', fontWeight: 600 }}>{f.wrong}</td>
                    <td style={{ textAlign: 'center', color: 'var(--text-muted)' }}>{f.missed}</td>
                    <td><RatingBadge em={f.exact_match} t={t} /></td>
                    <td>
                      <HBar value={f.exact_match} color={fieldColors[key] || '#60a5fa'} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── Bottom Grid: GPU Profiler + Processing Stats ─ */}
        <div className="bench-bottom-grid">

          {/* GPU Profiler */}
          <div className="card fade-in-up">
            <div className="bench-section-header">
              <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--accent-cyan)' }}>memory</span>
              <h2>{t('benchGpuProfile')}</h2>
            </div>
            <div className="bench-profiler-stats">
              <div className="bench-profiler-stat">
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>timer</span>
                <span>{t('benchTotalTime')}: <strong>{p.total_time_s}s</strong></span>
              </div>
              <div className="bench-profiler-stat">
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent-error)' }}>memory</span>
                <span>{t('benchPeakVRAM')}: <strong>{(p.peak_vram_mb / 1024).toFixed(1)} GB</strong></span>
              </div>
            </div>
            {p.stages.map((s, i) => {
              const pct = (s.latency_s / p.total_time_s) * 100
              const isMax = s.latency_s === Math.max(...p.stages.map(x => x.latency_s))
              return (
                <div key={i} className="bench-profiler-row">
                  <div className="bench-profiler-label">
                    <span style={{ fontSize: 12, fontWeight: 600, color: isMax ? 'var(--accent-error)' : 'var(--text-primary)' }}>
                      {s.stage}
                    </span>
                    <span style={{ fontSize: 11, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      {s.latency_s.toFixed(2)}s
                    </span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <HBar value={pct} maxValue={100} color={isMax ? '#f87171' : '#60a5fa'} height={6} />
                    <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', minWidth: 36, textAlign: 'right' }}>
                      {pct.toFixed(0)}%
                    </span>
                  </div>
                  {s.vram_peak_mb > 0 && (
                    <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>
                      VRAM: {s.vram_peak_mb >= 1024 ? `${(s.vram_peak_mb / 1024).toFixed(1)} GB` : `${s.vram_peak_mb} MB`}
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {/* Processing Stats + Model Stack */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            <div className="card fade-in-up">
              <div className="bench-section-header">
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--accent-success)' }}>speed</span>
                <h2>{t('benchProcessingStats')}</h2>
              </div>
              <div className="bench-stats-grid">
                <StatPill icon="timer" label={t('benchAvgTime')} value={formatTime(b.processing_time.mean_seconds)} color="#60a5fa" />
                <StatPill icon="bolt" label={t('benchMinTime')} value={formatTime(b.processing_time.min_seconds)} color="#34d399" />
                <StatPill icon="hourglass_top" label={t('benchMaxTime')} value={formatTime(b.processing_time.max_seconds)} color="#f87171" />
                <StatPill icon="schedule" label={t('benchTotalTime')} value={formatTime(b.processing_time.total_seconds)} color="#a78bfa" />
              </div>
            </div>

            <div className="card fade-in-up">
              <div className="bench-section-header">
                <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--accent-purple)' }}>deployed_code</span>
                <h2>{t('benchModelStack')}</h2>
              </div>
              <div className="bench-model-stack">
                {[
                  { label: 'OCR Detect', value: 'EasyOCR', icon: 'search', color: '#60a5fa' },
                  { label: 'OCR Recognize', value: 'VietOCR vgg_transformer', icon: 'text_fields', color: '#34d399' },
                  { label: 'Stamp Detect', value: 'YOLOv8x (best.pt)', icon: 'stamp', color: '#f87171' },
                  { label: 'Stamp Matting', value: 'HybridStampMatting', icon: 'auto_fix', color: '#fbbf24' },
                  { label: 'LLM Extract', value: 'Qwen2.5-7B (Ollama)', icon: 'psychology', color: '#a78bfa' },
                  { label: 'Layout', value: 'NĐ30 Rule-based', icon: 'grid_view', color: '#22d3ee' },
                ].map((m, i) => (
                  <div key={i} className="bench-model-row">
                    <div className="bench-model-icon" style={{ background: `${m.color}14` }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 16, color: m.color }}>{m.icon}</span>
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 10, color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em' }}>{m.label}</div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{m.value}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

      </div>
    </>
  )
}
