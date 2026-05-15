import { NavLink, useNavigate } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import { useTheme } from '../ThemeContext'
import { useMobileSidebar } from '../hooks/useMobileSidebar'
import { useSystemStatus } from '../hooks/useSystemStatus'
import StatusDot from '../ui/StatusDot'

const getNavItems = (t) => [
  { path: '/workspace', icon: 'document_scanner', label: t('navOCR') },
  { path: '/history', icon: 'fact_check', label: t('navHistory') },
]

const getFooterItems = (t) => [
  { path: '/benchmark', icon: 'science', label: t('navBenchmark') },
  { path: '/dashboard', icon: 'monitoring', label: t('navSystem') },
]

export default function SideNavBar() {
  const navigate = useNavigate()
  const { locale, toggleLocale, t } = useLocale()
  const { isDark, toggleTheme } = useTheme()
  const { isOpen, close } = useMobileSidebar()
  const systemStatus = useSystemStatus()

  // Close sidebar on route change (mobile)
  const handleNavClick = () => close()

  return (
    <>
      <nav className={`sidenav ${isOpen ? 'open' : ''}`}>
        {/* Brand */}
        <div className="sidenav-brand">
          <div className="sidenav-brand-icon">AI</div>
          <div>
            <h2>{t('brandTitle')}</h2>
            <p>{t('brandSub')}</p>
          </div>
        </div>

        {/* Upload Button */}
        <button className="sidenav-upload-btn" onClick={() => { navigate('/workspace', { state: { autoOpenUpload: true } }); close() }}>
          <span className="material-symbols-outlined" style={{ fontSize: 18 }}>add</span>
          <span>{t('uploadBtn')}</span>
        </button>

        {/* Navigation */}
        <div className="sidenav-links">
          {getNavItems(t).map(item => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) => `sidenav-link ${isActive ? 'active' : ''}`}
              end={item.path === '/'}
              onClick={handleNavClick}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              <span>{item.label}</span>
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
              onClick={handleNavClick}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}

          {/* Theme Toggle */}
          <button className="theme-toggle" onClick={toggleTheme} aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}>
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              {isDark ? 'light_mode' : 'dark_mode'}
            </span>
            <span>{isDark ? t('themeLight') : t('themeDark')}</span>
          </button>

          {/* Locale Toggle */}
          <button className="locale-toggle" onClick={toggleLocale} aria-label="Toggle language">
            <span className="flag">{locale === 'vi' ? '🇻🇳' : '🇺🇸'}</span>
            <span>{locale === 'vi' ? 'Tiếng Việt' : 'English'}</span>
          </button>

          {/* Status Indicator (Mobile Only) */}
          <div className="mobile-status">
            <StatusDot status={systemStatus} />
            {t('localNode')}
          </div>

          <div style={{
            marginTop: 10, padding: '8px 12px', borderRadius: 8,
            background: 'var(--accent-muted)', border: '1px solid var(--border)',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 10, fontWeight: 700, color: 'var(--accent)', letterSpacing: '0.05em' }}>NCKH SV 2026</div>
            <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 2 }}>OCR + LLM Pipeline</div>
          </div>
        </div>
      </nav>

      {/* Mobile overlay */}
      <div
        className={`sidebar-overlay ${isOpen ? 'visible' : ''}`}
        onClick={close}
      />
    </>
  )
}
