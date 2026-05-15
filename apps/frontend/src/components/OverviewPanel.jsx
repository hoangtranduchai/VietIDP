import { useState } from 'react'
import { useLocale } from '../LocaleContext'

/* ─── Collapsible Insight Card ─────────────────────────────── */
function InsightCard({ idx, title, body }) {
  const [open, setOpen] = useState(idx === 0)
  return (
    <div className="insight-accordion">
      <button className="insight-accordion-header" onClick={() => setOpen(!open)}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span className={`insight-num ${open ? 'active' : ''}`}>{idx + 1}</span>
          <span style={{ fontWeight: 600, fontSize: 13 }}>{title}</span>
        </div>
        <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--text-muted)', transition: 'transform 0.2s' , transform: open ? 'rotate(180deg)' : 'none' }}>
          expand_more
        </span>
      </button>
      <div className={`insight-accordion-body ${open ? 'open' : ''}`}>
        <div className="insight-accordion-content">{body}</div>
      </div>
    </div>
  )
}

/* ─── Entity Badge Group ──────────────────────────────────── */
function EntityBadges({ label, icon, items, color }) {
  if (!items?.length) return null
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <span className="material-symbols-outlined" style={{ fontSize: 14, color }}>{icon}</span>
        <span className="entity-label">{label}</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {items.map((item, i) => (
          <span key={i} className="entity-badge" style={{
            background: `${color}14`, color, borderColor: `${color}30`,
          }}>{item}</span>
        ))}
      </div>
    </div>
  )
}

/* ─── Mini Donut Chart (CSS-only) ──────────────────────────── */
function MiniDonut({ value, size = 48, color = '#34d399' }) {
  const pct = Math.round((value || 0) * 100)
  const r = (size - 6) / 2
  const circ = 2 * Math.PI * r
  const offset = circ * (1 - (value || 0))
  return (
    <div style={{ width: size, height: size, position: 'relative', flexShrink: 0 }}>
      <svg viewBox={`0 0 ${size} ${size}`} style={{ transform: 'rotate(-90deg)' }}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="var(--border)" strokeWidth="5" />
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={`${circ - offset} ${offset}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 1s var(--ease)' }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontSize: size * 0.22, fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-display)' }}>{pct}%</span>
      </div>
    </div>
  )
}

/* ─── Main Panel ──────────────────────────────────────────── */
export default function OverviewPanel({ data = {} }) {
  const { t } = useLocale()

  // Transform extraction data into display format
  const d = {
    meta: {
      loai: data.loai_van_ban || '—',
      so_hieu: data.so_hieu || '—',
      ngay: data.ngay_ban_hanh || '—',
      co_quan: data.co_quan_ban_hanh || '—',
      nguoi_ky: data.nguoi_ky || '—',
      linh_vuc: data.linh_vuc || '—',
      hieu_luc: data.thoi_han_hieu_luc || data.ngay_hieu_luc || '—',
    },
    tldr: data.trich_yeu || data.tom_tat_ngan || '',
    tom_tat: data.tom_tat_day_du || '',
    insights: data.diem_chinh?.map((p, i) => ({ title: `${t('insightPoint')} ${i + 1}`, body: p })) || [],
    entities: {
      organizations: data.co_quan_ban_hanh ? [data.co_quan_ban_hanh] : [],
      people: data.nguoi_ky ? [data.nguoi_ky] : [],
      laws: data.van_ban_lien_quan || [],
    },
    keywords: data.tu_khoa || [],
    stats: {
      time: data.processing_time,
      confidence: data.ocr_confidence,
      stamps: data.total_stamps || 0,
    },
    fieldConfidence: data._confidence || {},
  }

  const hasData = d.tldr || d.meta.so_hieu !== '—'

  return (
    <div className="overview-panel">
      {/* ── Panel Header ────────────────────────────────────── */}
      <div className="pane-header">
        <span className="pane-header-label">
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>dashboard</span>
          {t('tabOverview')}
        </span>
        {hasData && (
          <span className="pane-header-badge">{d.meta.loai}</span>
        )}
      </div>

      <div className="overview-scroll">
        {!hasData ? (
          /* ── Empty State ─────────────────────────────────── */
          <div style={{ textAlign: 'center', padding: '60px 32px', color: 'var(--text-muted)' }}>
            <span className="material-symbols-outlined float" style={{ fontSize: 52, opacity: 0.25, color: 'var(--accent)' }}>analytics</span>
            <p style={{ marginTop: 16, fontSize: 13 }}>{t('noData')}</p>
          </div>
        ) : (
          <div className="overview-content stagger">

            {/* ── 1. Document Identity Card ─────────────────── */}
            <div className="doc-identity-card fade-in-up">
              <div className="doc-identity-icon">
                <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--accent)' }}>description</span>
              </div>
              <div className="doc-identity-info">
                <div className="doc-identity-title">{d.meta.loai} · {d.meta.so_hieu}</div>
                <div className="doc-identity-date">
                  <span className="material-symbols-outlined" style={{ fontSize: 12 }}>calendar_today</span>
                  {d.meta.ngay}
                </div>
              </div>
            </div>

            {/* ── 2. Quick Meta Row ─────────────────────────── */}
            <div className="meta-cards-row fade-in-up">
              {[
                { icon: 'apartment', label: t('resultsIssuingAuth'), value: d.meta.co_quan, color: 'var(--accent)' },
                { icon: 'person', label: t('resultsSigner'), value: d.meta.nguoi_ky, color: 'var(--accent-purple)' },
                { icon: 'event', label: t('resultsEffective'), value: d.meta.hieu_luc, color: 'var(--accent-warning)' },
              ].map(({ icon, label, value, color }) => (
                <div key={label} className="meta-card">
                  <div className="meta-card-icon" style={{ background: `${color}14` }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 16, color }}>{icon}</span>
                  </div>
                  <div className="meta-card-text">
                    <div className="meta-card-label">{label}</div>
                    <div className="meta-card-value">{value}</div>
                  </div>
                </div>
              ))}
            </div>

            {/* ── 3. Quick Stats Bar ────────────────────────── */}
            {(d.stats.time || d.stats.confidence || d.stats.stamps > 0) && (
              <div className="quick-stats-bar fade-in-up" style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                {d.stats.confidence && (
                  <MiniDonut value={d.stats.confidence} size={52} color="var(--accent-success)" />
                )}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, flex: 1 }}>
                  {d.stats.time && (
                    <div className="quick-stat">
                      <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--accent-cyan)' }}>timer</span>
                      <span>{d.stats.time}s</span>
                    </div>
                  )}
                  {d.stats.confidence && (
                    <div className="quick-stat">
                      <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--accent-success)' }}>verified</span>
                      <span>{Math.round(d.stats.confidence * 100)}% OCR</span>
                    </div>
                  )}
                  {d.stats.stamps > 0 && (
                    <div className="quick-stat">
                      <span className="material-symbols-outlined" style={{ fontSize: 14, color: 'var(--accent-error)' }}>stamp</span>
                      <span>{d.stats.stamps} {t('stampsFound')}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* ── 3b. Field Confidence Bars ───────────────────── */}
            {Object.keys(d.fieldConfidence).length > 0 && (
              <div className="fade-in-up" style={{
                background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)', padding: 14, marginTop: -4,
              }}>
                <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 10 }}>
                  Field Confidence
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {Object.entries(d.fieldConfidence).map(([key, val]) => {
                    const pct = Math.round((val || 0) * 100)
                    const color = pct >= 95 ? 'var(--accent-success)' : pct >= 80 ? 'var(--accent-warning)' : 'var(--accent-error)'
                    return (
                      <div key={key} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', minWidth: 100, textAlign: 'right' }}>{key}</span>
                        <div style={{ flex: 1, height: 5, borderRadius: 3, background: 'var(--bg-hover)', overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${pct}%`, borderRadius: 3, background: color, transition: 'width 1s var(--ease)' }} />
                        </div>
                        <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', fontWeight: 700, color, minWidth: 30, textAlign: 'right' }}>{pct}%</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}

            {/* ── 4. TL;DR Hero ─────────────────────────────── */}
            {d.tldr && (
              <div className="tldr-hero fade-in-up">
                <div className="tldr-hero-label">
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>lightbulb</span>
                  <span>{t('resultsTLDR')}</span>
                </div>
                <p className="tldr-hero-text">{d.tldr}</p>
              </div>
            )}

            {/* ── 5. Entity Badges + Keywords ───────────────── */}
            <div className="entity-section fade-in-up">
              <h3 className="section-title">
                <span className="material-symbols-outlined" style={{ fontSize: 16 }}>account_tree</span>
                {t('entitiesTitle')}
              </h3>
              <EntityBadges label={t('resultsOrgs')} icon="apartment" items={d.entities.organizations} color="#60a5fa" />
              <EntityBadges label={t('resultsPeople')} icon="person" items={d.entities.people} color="#a78bfa" />
              <EntityBadges label={t('resultsLaws')} icon="gavel" items={d.entities.laws} color="#f97316" />

              {d.keywords.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div className="entity-label" style={{ marginBottom: 8 }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 13, color: 'var(--accent-cyan)', verticalAlign: 'middle', marginRight: 4 }}>sell</span>
                    {t('resultsKeywords')}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                    {d.keywords.map((k, i) => (
                      <span key={i} className="badge badge-blue">{k}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* ── 6. Full Summary ────────────────────────────── */}
            {d.tom_tat && (
              <section className="overview-section fade-in-up">
                <h3 className="section-title">
                  <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>menu_book</span>
                  {t('resultsFullSummary')}
                </h3>
                <div className="summary-card">{d.tom_tat}</div>
              </section>
            )}

            {/* ── 7. Key Insights Accordion ──────────────────── */}
            {d.insights.length > 0 && (
              <section className="overview-section fade-in-up">
                <h3 className="section-title">
                  <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>tag</span>
                  {t('resultsKeyInsights')}
                </h3>
                {d.insights.map((item, i) => <InsightCard key={i} idx={i} {...item} />)}
              </section>
            )}

          </div>
        )}
      </div>
    </div>
  )
}
