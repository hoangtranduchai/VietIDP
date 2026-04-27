import { useState } from 'react'
import { useLocale } from '../LocaleContext'

function InsightCard({ idx, title, body }) {
  const [open, setOpen] = useState(idx === 0)
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 8, background: 'var(--bg-elevated)', border: '1px solid var(--border)' }}>
      <button onClick={() => setOpen(!open)} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 16px', background: 'transparent', border: 'none', cursor: 'pointer',
        fontFamily: 'inherit', textAlign: 'left', gap: 12, color: 'var(--text-primary)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            width: 26, height: 26, borderRadius: 8,
            background: open ? 'var(--accent)' : 'var(--bg-hover)',
            color: open ? 'white' : 'var(--text-muted)',
            fontSize: 12, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s',
          }}>{idx + 1}</span>
          <span style={{ fontWeight: 600, fontSize: 14 }}>{title}</span>
        </div>
        <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--text-muted)' }}>
          {open ? 'expand_less' : 'expand_more'}
        </span>
      </button>
      {open && (
        <div style={{ padding: '0 16px 16px 54px', fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.85 }}>
          {body}
        </div>
      )}
    </div>
  )
}

function EntityBadges({ label, icon, items, color }) {
  if (!items?.length) return null
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8 }}>
        <span className="material-symbols-outlined" style={{ fontSize: 14, color }}>{icon}</span>
        <span style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {items.map((item, i) => (
          <span key={i} style={{
            padding: '4px 10px', borderRadius: 20, fontSize: 12, fontWeight: 500,
            background: `${color}14`, color, border: `1px solid ${color}30`,
          }}>{item}</span>
        ))}
      </div>
    </div>
  )
}

export default function InsightsPanel({ data = {} }) {
  const { t } = useLocale()
  
  // Transform data to match the expected format, using fallbacks where necessary
  const d = {
    meta: {
      loai: data.loai_van_ban || '—',
      so_hieu: data.so_hieu || '—',
      ngay: data.ngay_ban_hanh || '—',
      co_quan: data.co_quan_ban_hanh || '—',
      nguoi_ky: data.nguoi_ky || '—'
    },
    tldr: data.trich_yeu || data.tom_tat_ngan || t('noData'),
    tom_tat: data.tom_tat_day_du || '',
    insights: data.diem_chinh?.map((p, i) => ({ title: `Điểm ${i+1}`, body: p })) || [],
    entities: {
      organizations: data.co_quan_ban_hanh ? [data.co_quan_ban_hanh] : [],
      people: data.nguoi_ky ? [data.nguoi_ky] : [],
      laws: data.van_ban_lien_quan || []
    },
    keywords: data.tu_khoa || []
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', minHeight: 0 }}>
      <div className="pane-header">
        <span className="pane-header-label">
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent-purple)' }}>insights</span>
          Báo cáo phân tích
        </span>
      </div>
      <div className="pane-body" style={{ padding: 20 }}>
        
        {/* TL;DR */}
        <div style={{
          background: 'linear-gradient(135deg, rgba(96,165,250,0.08), rgba(52,211,153,0.06))',
          border: '1px solid rgba(96,165,250,0.15)', borderRadius: 'var(--radius)', padding: '20px 24px', marginBottom: 24,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>lightbulb</span>
            <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: 0.6 }}>Tóm tắt nhanh (TL;DR)</span>
          </div>
          <p style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.65 }}>{d.tldr}</p>
        </div>

        {/* Entities Section */}
        <section style={{ marginBottom: 28, background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius)', padding: 16 }}>
          <h3 style={{ fontSize: 12, fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 16, display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>account_tree</span>
            Thực thể pháp lý
          </h3>
          <EntityBadges label="Tổ chức / Cơ quan" icon="apartment" items={d.entities.organizations} color="#60a5fa" />
          <EntityBadges label="Nhân vật" icon="person" items={d.entities.people} color="#a78bfa" />
          <EntityBadges label="Văn bản liên quan" icon="gavel" items={d.entities.laws} color="#f97316" />
          
          {d.keywords?.length > 0 && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>Từ khóa chính</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {d.keywords.map((k, i) => (
                  <span key={i} className="badge badge-blue">{k}</span>
                ))}
              </div>
            </div>
          )}
        </section>

        {/* Full summary if available */}
        {d.tom_tat && (
          <section style={{ marginBottom: 28 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>menu_book</span>
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Tóm tắt chi tiết</h3>
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.9, background: 'var(--bg-elevated)', padding: 16, borderRadius: 'var(--radius)', border: '1px solid var(--border)' }}>{d.tom_tat}</div>
          </section>
        )}

        {/* Key Insights if available */}
        {d.insights?.length > 0 && (
          <section style={{ marginBottom: 28 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>tag</span>
              <h3 style={{ fontSize: 14, fontWeight: 700 }}>Điểm nhấn trọng tâm</h3>
            </div>
            {d.insights.map((item, i) => <InsightCard key={i} idx={i} {...item} />)}
          </section>
        )}

      </div>
    </div>
  )
}
