import { NavLink, useNavigate } from 'react-router-dom'
import { useLocale } from '../LocaleContext'

const getNavItems = (t) => [
  { path: '/', icon: 'cloud_upload', label: t('navIngestion') },
  { path: '/workspace', icon: 'document_scanner', label: t('navOCR') },
  { path: '/summarize', icon: 'auto_awesome', label: 'Summarize' },
  { path: '/chat', icon: 'psychology', label: t('navChat') },
  { path: '/history', icon: 'fact_check', label: t('navHistory') },
]

const getFooterItems = (t) => [
  { path: '/dashboard', icon: 'monitoring', label: t('navSystem') },
]

export default function SideNavBar() {
  const navigate = useNavigate()
  const { locale, toggleLocale, t } = useLocale()

  return (
    <nav className="sidenav">
      {/* Brand */}
      <div className="sidenav-brand">
        <div className="sidenav-brand-icon">AI</div>
        <div>
          <h2>{t('brandTitle')}</h2>
          <p>{t('brandSub')}</p>
        </div>
      </div>

      {/* Upload Button */}
      <button className="sidenav-upload-btn" onClick={() => navigate('/')}>
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
        {t('uploadBtn')}
      </button>

      {/* Navigation */}
      <div className="sidenav-links">
        {getNavItems(t).map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `sidenav-link ${isActive ? 'active' : ''}`}
            end={item.path === '/'}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </div>

      {/* Footer */}
      <div className="sidenav-footer">
        {getFooterItems(t).map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) => `sidenav-link ${isActive ? 'active' : ''}`}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}

        <button className="locale-toggle" onClick={toggleLocale}>
          <span className="flag">{locale === 'vi' ? '🇻🇳' : '🇺🇸'}</span>
          <span>{locale === 'vi' ? 'Tiếng Việt' : 'English'}</span>
        </button>

        <div style={{
          marginTop: 10, padding: '8px 12px', borderRadius: 8,
          background: 'var(--accent-muted)', border: '1px solid rgba(96,165,250,0.15)',
          textAlign: 'center',
        }}>
          <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.05em' }}>NCKH SV 2026</div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>OCR + LLM Pipeline</div>
        </div>
      </div>
    </nav>
  )
}
