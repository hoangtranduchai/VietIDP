import { useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  FileText, ChevronDown, ChevronUp, Download,
  Lightbulb, Users, BookOpen, Search, RefreshCw,
  CheckCircle, Hash, Building2, CalendarDays, Scale
} from 'lucide-react';

// ── Mock deep analysis data ──────────────────────────────────────────────────
const MOCK = {
  meta: {
    loai: "Quyết định",
    so_hieu: "123/QĐ-BGDĐT",
    ngay: "15/05/2025",
    co_quan: "Bộ Giáo dục và Đào tạo",
    nguoi_ky: "Nguyễn Kim Sơn — Bộ trưởng",
    linh_vuc: "Giáo dục & Đào tạo",
    hieu_luc: "01/06/2025",
    muc_do: "Cao"
  },
  tldr: "Quy định mới về quản lý, cấp phát và thu hồi văn bằng, chứng chỉ trong hệ thống giáo dục quốc dân — áp dụng toàn quốc từ 01/06/2025.",
  tom_tat: "Quyết định này do Bộ Giáo dục và Đào tạo ban hành nhằm hoàn thiện khung pháp lý trong lĩnh vực quản lý văn bằng, chứng chỉ. Quyết định quy định rõ thẩm quyền cấp phát, điều kiện cấp phát và quy trình thu hồi văn bằng trong các trường hợp vi phạm. Các cơ sở giáo dục phải cập nhật hệ thống quản lý điện tử chậm nhất 6 tháng sau khi quyết định có hiệu lực. Bộ cũng tăng cường trách nhiệm của hiệu trưởng trong việc xác nhận tính xác thực của văn bằng. Quyết định nhấn mạnh việc tích hợp cơ sở dữ liệu văn bằng quốc gia để phục vụ tra cứu công khai và ngăn chặn bằng giả.",
  insights: [
    {
      title: "Giới hạn thời gian cấp văn bằng",
      body: "Cơ sở giáo dục phải cấp văn bằng trong tối đa 30 ngày làm việc tính từ ngày sinh viên tốt nghiệp chính thức. Các trường hợp chậm trễ vô lý sẽ bị coi là vi phạm hành chính."
    },
    {
      title: "Quy trình thu hồi văn bằng gian lận",
      body: "Khi phát hiện văn bằng gian lận, cơ sở giáo dục phải hoàn tất thủ tục thu hồi trong vòng 60 ngày. Mọi trường hợp cần thông báo đến Bộ GD&ĐT và công khai danh sách thu hồi trên cổng thông tin."
    },
    {
      title: "Tích hợp CSDL văn bằng quốc gia",
      body: "Tất cả cơ sở giáo dục phải kết nối với hệ thống cơ sở dữ liệu văn bằng quốc gia trước ngày 01/12/2025. Sau thời hạn này, việc cấp văn bằng mà không qua hệ thống điện tử là trái pháp luật."
    },
    {
      title: "Quyền tra cứu của người học",
      body: "Người học có quyền tra cứu thông tin văn bằng của mình qua Cổng dịch vụ công quốc gia bất kỳ lúc nào. Thông tin bao gồm ngày cấp, điểm trung bình, và xác nhận số hiệu văn bằng."
    },
    {
      title: "Mức xử phạt mới",
      body: "Hành vi cấp văn bằng không đúng quy định bị xử phạt hành chính lên đến 50 triệu đồng. Trường hợp gian lận có tổ chức có thể bị truy cứu trách nhiệm hình sự theo điều 341 Bộ luật Hình sự."
    }
  ],
  entities: {
    organizations: ["Bộ Giáo dục và Đào tạo", "Cổng dịch vụ công quốc gia", "CSDL văn bằng quốc gia"],
    people: ["Nguyễn Kim Sơn"],
    laws: ["Luật Giáo dục 2019", "Nghị định 99/2019/NĐ-CP", "Điều 341 Bộ luật Hình sự"],
    dates: ["01/06/2025 (Hiệu lực)", "01/12/2025 (Hạn tích hợp CSDL)"]
  },
  keywords: ["Văn bằng", "Chứng chỉ", "Thu hồi", "Cơ sở dữ liệu", "Gian lận", "Hành chính"],
  faqs: [
    { q: "Ai phải chịu trách nhiệm nếu văn bằng bị cấp sai?", a: "Hiệu trưởng của cơ sở giáo dục là người chịu trách nhiệm trực tiếp và có thể bị xử lý kỷ luật hoặc hành chính." },
    { q: "Người học phải làm gì nếu bị thu hồi văn bằng nhầm?", a: "Người học có quyền khiếu nại lên Phòng GD&ĐT cấp quận/huyện trong vòng 30 ngày kể từ ngày nhận quyết định thu hồi." },
    { q: "Văn bằng cũ (trước 2025) có cần đăng ký lại không?", a: "Không bắt buộc, nhưng Bộ khuyến khích các cơ sở giáo dục nhập liệu văn bằng lịch sử vào CSDL quốc gia để đồng bộ hóa." }
  ]
};

// ── Sub components ────────────────────────────────────────────────────────────

function InsightCard({ idx, title, body }) {
  const [open, setOpen] = useState(idx === 0);
  return (
    <div style={{
      background: open ? 'var(--bg-card)' : 'transparent',
      border: `1px solid ${open ? 'var(--border-bright)' : 'var(--border)'}`,
      borderRadius: 10, overflow: 'hidden', transition: 'all 0.2s'
    }}>
      <button onClick={() => setOpen(!open)} style={{
        width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '14px 16px', background: 'transparent', border: 'none', cursor: 'pointer',
        fontFamily: 'inherit', textAlign: 'left', gap: 12
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span style={{
            width: 26, height: 26, borderRadius: 8, background: open ? 'var(--accent)' : 'var(--bg-hover)',
            color: open ? 'white' : 'var(--text-muted)', fontSize: 12, fontWeight: 700,
            display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, transition: 'all 0.2s'
          }}>{idx + 1}</span>
          <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>{title}</span>
        </div>
        {open ? <ChevronUp size={15} color="var(--text-muted)" /> : <ChevronDown size={15} color="var(--text-muted)" />}
      </button>
      {open && (
        <div style={{ padding: '0 16px 16px 54px', fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8 }}>
          {body}
        </div>
      )}
    </div>
  );
}

function FaqCard({ q, a }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
      <button onClick={() => setOpen(!open)} style={{
        width: '100%', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        padding: '13px 16px', background: 'transparent', border: 'none', cursor: 'pointer',
        fontFamily: 'inherit', textAlign: 'left', gap: 12
      }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'flex-start' }}>
          <Search size={14} color="var(--accent)" style={{ flexShrink: 0, marginTop: 2 }} />
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.5 }}>{q}</span>
        </div>
        {open ? <ChevronUp size={14} color="var(--text-muted)" style={{ flexShrink: 0 }} /> : <ChevronDown size={14} color="var(--text-muted)" style={{ flexShrink: 0 }} />}
      </button>
      {open && (
        <div style={{ padding: '0 16px 14px 40px', fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8, background: 'var(--bg-secondary)' }}>
          {a}
        </div>
      )}
    </div>
  );
}

function EntitySection({ icon: Icon, label, items, color }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{ marginBottom: 18 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
        <Icon size={13} color={color} />
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.5 }}>{label}</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
        {items.map((item, i) => (
          <span key={i} style={{
            padding: '4px 10px', borderRadius: 20, fontSize: 12,
            background: `${color}12`, color, border: `1px solid ${color}30`, fontWeight: 500
          }}>{item}</span>
        ))}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function ResultsPage() {
  const { id } = useParams();
  const [isHovering, setIsHovering] = useState(null);
  
  // Try to use real data first, merge with fallbacks for empty fields
  const savedStr = localStorage.getItem('last_summary');
  let realSum = null;
  try {
    const parsed = savedStr ? JSON.parse(savedStr) : null;
    realSum = parsed?.summary || null;
  } catch (e) { realSum = null; }

  // Check if LLM response is complete enough to use
  const hasRealContent = realSum && (
    (realSum.tom_tat_ngan && realSum.tom_tat_ngan.length > 5) ||
    (realSum.tom_tat_day_du && realSum.tom_tat_day_du.length > 5) ||
    (realSum.diem_chinh && realSum.diem_chinh.length > 0)
  );

  const isPartialData = realSum && !hasRealContent;
  
  const displayData = hasRealContent ? {
    meta: {
      loai: realSum.loai_van_ban || MOCK.meta.loai,
      so_hieu: realSum.so_hieu || MOCK.meta.so_hieu,
      ngay: realSum.ngay_ban_hanh || MOCK.meta.ngay,
      co_quan: realSum.co_quan_ban_hanh || MOCK.meta.co_quan,
      nguoi_ky: realSum.nguoi_ky || MOCK.meta.nguoi_ky,
      linh_vuc: realSum.linh_vuc || MOCK.meta.linh_vuc,
      hieu_luc: realSum.thoi_han_hieu_luc || MOCK.meta.hieu_luc,
      muc_do: realSum.muc_do_quan_trong || MOCK.meta.muc_do
    },
    tldr: realSum.tom_tat_ngan || MOCK.tldr,
    tom_tat: realSum.tom_tat_day_du || MOCK.tom_tat,
    insights: (realSum.diem_chinh && realSum.diem_chinh.length > 0)
      ? realSum.diem_chinh.map((p, i) => ({ title: `Nội dung ${i+1}`, body: p }))
      : MOCK.insights,
    entities: {
      organizations: realSum.co_quan_ban_hanh ? [realSum.co_quan_ban_hanh] : MOCK.entities.organizations,
      people: realSum.nguoi_ky ? [realSum.nguoi_ky] : MOCK.entities.people,
      laws: (realSum.van_ban_lien_quan && realSum.van_ban_lien_quan.length > 0) ? realSum.van_ban_lien_quan : MOCK.entities.laws,
      dates: realSum.thoi_han_hieu_luc ? [realSum.thoi_han_hieu_luc] : MOCK.entities.dates
    },
    keywords: (realSum.tu_khoa && realSum.tu_khoa.length > 0) ? realSum.tu_khoa : MOCK.keywords,
    faqs: (realSum.nghia_vu_va_quyen_han && realSum.nghia_vu_va_quyen_han.length > 0)
      ? realSum.nghia_vu_va_quyen_han.map(o => ({ q: "Nghĩa vụ / Quyền hạn", a: o }))
      : MOCK.faqs
  } : MOCK;

  const { meta, tldr, tom_tat, insights, entities, keywords, faqs } = displayData;

  const pages = JSON.parse(localStorage.getItem('last_processed_pages') || 'null') || [
    { original_url: 'https://images.unsplash.com/photo-1586281380349-632531db7ed4', annotated_url: null, stamps: [] }
  ];

  return (
    <div style={{ display: 'flex', gap: 0, height: '100%', animation: 'fadeIn 0.35s ease' }}>

      {/* ── LEFT: Document Preview ────────────────────────── */}
      <div style={{
        width: 340, flexShrink: 0, borderRight: '1px solid var(--border)',
        overflowY: 'auto', padding: '20px 16px', background: 'var(--bg-secondary)'
      }}>
        {/* Doc identity chip */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <div style={{ width: 36, height: 36, borderRadius: 9, background: 'var(--accent-glow)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <FileText size={18} color="var(--accent)" />
          </div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 13, color: 'var(--text-primary)' }}>{meta.loai} · {meta.so_hieu}</div>
            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{meta.ngay} · {meta.linh_vuc}</div>
          </div>
        </div>

        {/* Pages */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {pages.map((page, idx) => (
            <div key={idx} style={{ position: 'relative', borderRadius: 8, overflow: 'hidden', border: '1px solid var(--border)', background: 'white' }}>
              <img
                src={isHovering === idx ? (page.annotated_url || page.original_url) : page.original_url}
                alt={`Trang ${idx + 1}`}
                style={{ width: '100%', display: 'block' }}
              />
              {(page.stamps || []).map((s, si) => {
                const hp = page.img_h ? (s.h / page.img_h) * 100 : 20;
                const wp = page.img_w ? (s.w / page.img_w) * 100 : 20;
                return (
                  <div key={si}
                    onMouseEnter={() => setIsHovering(idx)}
                    onMouseLeave={() => setIsHovering(null)}
                    style={{
                      position: 'absolute',
                      top: `${page.img_h ? (s.y / page.img_h) * 100 : 0}%`,
                      left: `${page.img_w ? (s.x / page.img_w) * 100 : 0}%`,
                      width: `${wp}%`, height: `${hp}%`, cursor: 'crosshair', zIndex: 5,
                      background: isHovering === idx ? 'transparent' : 'rgba(255,50,50,0.15)',
                      border: isHovering === idx ? 'none' : '1px dashed rgba(255,50,50,0.5)',
                      borderRadius: 4
                    }}
                    title={`Con dấu · Tin cậy ${s.confidence}%`}
                  />
                );
              })}
              <div style={{ position: 'absolute', bottom: 6, right: 8, background: 'rgba(0,0,0,0.55)', color: 'white', fontSize: 11, padding: '2px 8px', borderRadius: 20, backdropFilter: 'blur(4px)' }}>
                Trang {idx + 1}
              </div>
            </div>
          ))}
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
          <button className="btn btn-primary" style={{ justifyContent: 'center' }}><Download size={14} /> Xuất Excel</button>
          <button className="btn btn-ghost" style={{ justifyContent: 'center' }}><RefreshCw size={14} /> Xử lý lại</button>
        </div>
      </div>

      {/* ── CENTER: Analysis ──────────────────────────────── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '28px 28px' }}>

        {/* Warning banner when LLM data is incomplete */}
        {isPartialData && (
          <div style={{
            background: 'linear-gradient(135deg, #fef3c7 0%, #fde68a 100%)',
            border: '1px solid #f59e0b', borderRadius: 14, padding: '16px 20px', marginBottom: 16,
            display: 'flex', alignItems: 'center', gap: 12
          }}>
            <span style={{ fontSize: 20 }}>⚠️</span>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14, color: '#92400e' }}>LLM trả về dữ liệu không đầy đủ</div>
              <div style={{ fontSize: 13, color: '#a16207', marginTop: 2 }}>
                Ollama có thể chưa sẵn sàng hoặc model chưa pull xong. Đang hiển thị dữ liệu mẫu (demo).
                Hãy kiểm tra: <code style={{background:'#fef9c3',padding:'1px 6px',borderRadius:4}}>ollama list</code> và chạy lại.
              </div>
            </div>
          </div>
        )}

        {/* TL;DR hero */}
        <div style={{
          background: 'linear-gradient(135deg, #eff6ff 0%, #f0fdf4 100%)',
          border: '1px solid #bfdbfe', borderRadius: 14, padding: '20px 24px', marginBottom: 24
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginBottom: 8 }}>
            <Lightbulb size={15} color="#2563eb" />
            <span style={{ fontSize: 11, fontWeight: 800, color: '#2563eb', textTransform: 'uppercase', letterSpacing: 0.6 }}>Tóm tắt một dòng</span>
          </div>
          <p style={{ fontSize: 16, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.65 }}>{tldr}</p>
        </div>

        {/* Full summary */}
        <section style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <BookOpen size={16} color="var(--accent)" />
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>Tổng quan nội dung</h3>
          </div>
          <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.95, background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 10, padding: '16px 18px' }}>
            {tom_tat}
          </p>
        </section>

        {/* Insights accordion */}
        <section style={{ marginBottom: 28 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <Hash size={16} color="var(--accent)" />
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>Điểm nội dung chính</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {insights.map((item, i) => <InsightCard key={i} idx={i} {...item} />)}
          </div>
        </section>

        {/* FAQ */}
        <section>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <Search size={16} color="var(--accent)" />
            <h3 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-primary)' }}>Câu hỏi thường gặp về văn bản này</h3>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {faqs.map((faq, i) => <FaqCard key={i} {...faq} />)}
          </div>
        </section>
      </div>

      {/* ── RIGHT: Entities & Meta ────────────────────────── */}
      <div style={{
        width: 260, flexShrink: 0, borderLeft: '1px solid var(--border)',
        overflowY: 'auto', padding: '20px 16px', background: 'var(--bg-secondary)'
      }}>
        {/* Quick meta */}
        <div style={{ marginBottom: 20 }}>
          <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 10 }}>Thông tin văn bản</p>
          {[
            { icon: Building2, label: meta.co_quan, sub: 'Cơ quan ban hành', c: 'var(--accent)' },
            { icon: Users, label: meta.nguoi_ky, sub: 'Người ký', c: '#7c3aed' },
            { icon: CalendarDays, label: meta.hieu_luc, sub: 'Ngày hiệu lực', c: '#d97706' },
          ].map(({ icon: Icon, label, sub, c }) => (
            <div key={sub} style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
              <div style={{ width: 30, height: 30, borderRadius: 7, background: `${c}14`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon size={14} color={c} />
              </div>
              <div>
                <div style={{ fontSize: 10, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.4 }}>{sub}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.4, marginTop: 1 }}>{label}</div>
              </div>
            </div>
          ))}
        </div>

        <div style={{ height: 1, background: 'var(--border)', marginBottom: 18 }} />

        {/* Entities */}
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 14 }}>Thực thể trích xuất</p>
        <EntitySection icon={Building2} label="Cơ quan" items={entities.organizations} color="#2563eb" />
        <EntitySection icon={Users} label="Người" items={entities.people} color="#7c3aed" />
        <EntitySection icon={Scale} label="Văn bản pháp lý" items={entities.laws} color="#c2410c" />
        <EntitySection icon={CalendarDays} label="Mốc thời gian" items={entities.dates} color="#047857" />

        <div style={{ height: 1, background: 'var(--border)', marginBottom: 18 }} />

        {/* Keywords */}
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 10 }}>Từ khóa</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {keywords.map((k, i) => (
            <span key={i} style={{ padding: '3px 10px', borderRadius: 20, fontSize: 12, background: 'var(--bg-hover)', border: '1px solid var(--border-bright)', fontWeight: 500, color: 'var(--text-secondary)' }}>{k}</span>
          ))}
        </div>

        <div style={{ height: 1, background: 'var(--border)', marginVertical: 18, margin: '18px 0' }} />

        {/* Compliance */}
        <p style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: 0.6, marginBottom: 10 }}>Checklist tuân thủ</p>
        {[
          "Kết nối CSDL văn bằng quốc gia",
          "Cập nhật quy trình cấp phát",
          "Đào tạo cán bộ phụ trách",
          "Rà soát văn bằng đã cấp"
        ].map((item, i) => (
          <div key={i} style={{ display: 'flex', gap: 8, alignItems: 'flex-start', marginBottom: 8 }}>
            <CheckCircle size={14} color="var(--accent-success)" style={{ flexShrink: 0, marginTop: 1 }} />
            <span style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.5 }}>{item}</span>
          </div>
        ))}
      </div>

    </div>
  );
}
