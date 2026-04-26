import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import TopBar from '../layouts/TopBar'
import { chatWithDocument } from '../services/api'

// ── Mock data for demo mode ──────────────────────────────────
const MOCK = {
  meta: { loai: "Quyết định", so_hieu: "123/QĐ-BGDĐT", ngay: "15/05/2025", co_quan: "Bộ Giáo dục và Đào tạo", nguoi_ky: "Nguyễn Kim Sơn — Bộ trưởng", linh_vuc: "Giáo dục & Đào tạo", hieu_luc: "01/06/2025" },
  tldr: "Quy định mới về quản lý, cấp phát và thu hồi văn bằng, chứng chỉ trong hệ thống giáo dục quốc dân.",
  tom_tat: "Quyết định quy định rõ thẩm quyền cấp phát, điều kiện cấp phát và quy trình thu hồi văn bằng trong các trường hợp vi phạm.",
  insights: [
    { title: "Giới hạn thời gian cấp văn bằng", body: "Cơ sở giáo dục phải cấp văn bằng trong tối đa 30 ngày làm việc." },
    { title: "Tích hợp CSDL văn bằng quốc gia", body: "Tất cả cơ sở giáo dục phải kết nối hệ thống CSDL trước 01/12/2025." },
    { title: "Mức xử phạt mới", body: "Cấp văn bằng không đúng quy định bị phạt lên đến 50 triệu đồng." },
  ],
  entities: {
    organizations: ["Bộ Giáo dục và Đào tạo"],
    people: ["Nguyễn Kim Sơn"],
    laws: ["Luật Giáo dục 2019", "Nghị định 99/2019/NĐ-CP"],
  },
  keywords: ["Văn bằng", "Chứng chỉ", "Thu hồi", "Gian lận"],
}

function InsightCard({ idx, title, body }) {
  const [open, setOpen] = useState(idx === 0)
  return (
    <div className="card" style={{ padding: 0, overflow: 'hidden', marginBottom: 8 }}>
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

export default function ResultsPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t } = useLocale()
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const [faqs, setFaqs] = useState([])

  // Load real data or fallback to mock
  let savedData = null
  try { savedData = JSON.parse(localStorage.getItem('last_summary'))?.summary } catch {}
  const hasReal = savedData?.tom_tat_ngan?.length > 5
  const d = hasReal ? {
    meta: { loai: savedData.loai_van_ban || '—', so_hieu: savedData.so_hieu || '—', ngay: savedData.ngay_ban_hanh || '—', co_quan: savedData.co_quan_ban_hanh || '—', nguoi_ky: savedData.nguoi_ky || '—', linh_vuc: savedData.linh_vuc || '—', hieu_luc: savedData.thoi_han_hieu_luc || '—' },
    tldr: savedData.tom_tat_ngan || '', tom_tat: savedData.tom_tat_day_du || '',
    insights: savedData.diem_chinh?.map((p, i) => ({ title: `Point ${i+1}`, body: p })) || [],
    entities: { organizations: savedData.co_quan_ban_hanh ? [savedData.co_quan_ban_hanh] : [], people: savedData.nguoi_ky ? [savedData.nguoi_ky] : [], laws: savedData.van_ban_lien_quan || [] },
    keywords: savedData.tu_khoa || [],
  } : MOCK

  const handleAsk = async (e) => {
    e.preventDefault()
    if (!chatInput.trim() || chatLoading) return
    const q = chatInput.trim()
    setChatInput('')
    setChatLoading(true)
    setFaqs(prev => [...prev, { q, a: '⏳ Analyzing...' }])
    try {
      // In ResultsPage, we might not have id but we use savedData text
      // if not available, fallback to mock text
      const context = savedData ? JSON.stringify(savedData) : JSON.stringify(MOCK)
      const res = await chatWithDocument(q, null, context)
      setFaqs(prev => prev.map((f, i) => i === prev.length - 1 ? { q, a: res.answer } : f))
    } catch {
      setFaqs(prev => prev.map((f, i) => i === prev.length - 1 ? { q, a: '❌ Connection error' } : f))
    }
    setChatLoading(false)
  }

  return (
    <>
      <TopBar />
      <div className="results-layout">

        {/* LEFT — Document Preview */}
        <div className="results-sidebar">
          {/* Doc identity */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <div style={{ width: 36, height: 36, borderRadius: 9, background: 'var(--accent-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--accent)' }}>description</span>
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>{d.meta.loai} · {d.meta.so_hieu}</div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{d.meta.ngay}</div>
            </div>
          </div>

          {/* Quick meta */}
          {[
            { icon: 'apartment', label: d.meta.co_quan, sub: t('resultsIssuingAuth'), c: 'var(--accent)' },
            { icon: 'person', label: d.meta.nguoi_ky, sub: t('resultsSigner'), c: 'var(--accent-purple)' },
            { icon: 'event', label: d.meta.hieu_luc, sub: t('resultsEffective'), c: 'var(--accent-warning)' },
          ].map(({ icon, label, sub, c }) => (
            <div key={sub} style={{ display: 'flex', gap: 10, padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
              <div style={{ width: 28, height: 28, borderRadius: 7, background: `${c}14`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14, color: c }}>{icon}</span>
              </div>
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.4 }}>{sub}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', marginTop: 1 }}>{label}</div>
              </div>
            </div>
          ))}

          <div style={{ marginTop: 12 }}>
            <EntityBadges label={t('resultsOrgs')} icon="apartment" items={d.entities.organizations} color="#60a5fa" />
            <EntityBadges label={t('resultsPeople')} icon="person" items={d.entities.people} color="#a78bfa" />
            <EntityBadges label={t('resultsLaws')} icon="gavel" items={d.entities.laws} color="#f97316" />
          </div>

          {d.keywords?.length > 0 && (
            <div>
              <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 8 }}>{t('resultsKeywords')}</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {d.keywords.map((k, i) => (
                  <span key={i} className="badge badge-blue">{k}</span>
                ))}
              </div>
            </div>
          )}

          <div style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', gap: 8, paddingTop: 12 }}>
            <button className="btn btn-primary" style={{ justifyContent: 'center', width: '100%' }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>download</span> {t('resultsExport')}
            </button>
            <button className="btn" style={{ justifyContent: 'center', width: '100%' }} onClick={() => navigate('/')}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>refresh</span> {t('resultsProcessAnother')}
            </button>
          </div>
        </div>

        {/* CENTER — Analysis */}
        <div className="results-main">

          {/* TL;DR */}
          <div style={{
            background: 'linear-gradient(135deg, rgba(96,165,250,0.08), rgba(52,211,153,0.06))',
            border: '1px solid rgba(96,165,250,0.15)', borderRadius: 'var(--radius)', padding: '20px 24px', marginBottom: 24,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>lightbulb</span>
              <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: 0.6 }}>{t('resultsTLDR')}</span>
            </div>
            <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.65 }}>{d.tldr}</p>
          </div>

          {/* Full summary */}
          {d.tom_tat && (
            <section style={{ marginBottom: 28 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>menu_book</span>
                <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t('resultsFullSummary')}</h3>
              </div>
              <div className="card" style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.9 }}>{d.tom_tat}</div>
            </section>
          )}

          {/* Key Insights */}
          {d.insights?.length > 0 && (
            <section style={{ marginBottom: 28 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>tag</span>
                <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t('resultsKeyInsights')}</h3>
              </div>
              {d.insights.map((item, i) => <InsightCard key={i} idx={i} {...item} />)}
            </section>
          )}

          {/* FAQ / Ask AI */}
          <section>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>forum</span>
              <h3 style={{ fontSize: 15, fontWeight: 700 }}>{t('resultsAskAI')}</h3>
            </div>
            {faqs.map((f, i) => (
              <div key={i} className="card" style={{ marginBottom: 8 }}>
                <div style={{ fontWeight: 600, fontSize: 14, marginBottom: 6, color: 'var(--accent)' }}>{f.q}</div>
                <div style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8 }}>{f.a}</div>
              </div>
            ))}
            <form onSubmit={handleAsk} style={{ display: 'flex', gap: 8, marginTop: 8 }}>
              <input
                value={chatInput} onChange={e => setChatInput(e.target.value)}
                placeholder={t('chatPlaceholder')}
                disabled={chatLoading}
                style={{
                  flex: 1, padding: '12px 16px', borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border)', background: 'var(--bg-primary)',
                  color: 'var(--text-primary)', fontSize: 13, fontFamily: 'var(--font)', outline: 'none',
                }}
              />
              <button type="submit" disabled={chatLoading} className="btn btn-primary" style={{ padding: '0 20px' }}>
                {chatLoading ? t('resultsAsking') : t('resultsAskBtn')}
              </button>
            </form>
          </section>
        </div>
      </div>
    </>
  )
}
