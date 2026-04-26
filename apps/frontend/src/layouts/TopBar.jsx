import { useLocale } from '../LocaleContext'
import { useMobileSidebar } from '../hooks/useMobileSidebar'
import { useSystemStatus } from '../hooks/useSystemStatus'
import StatusDot from '../ui/StatusDot'

/**
 * Shared TopBar layout — extracted from every page
 * Props:
 *   title     — override main title (default: appTitle from locale)
 *   pipeline  — optional array of { key, label, icon, completed, active }
 *   children  — right-side slot
 */
export default function TopBar({ title, pipeline, children }) {
  const { t } = useLocale()
  const { toggle } = useMobileSidebar()
  const systemStatus = useSystemStatus()

  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        {/* Hamburger — visible only on mobile via CSS */}
        <button className="mobile-menu-btn" onClick={toggle} aria-label="Toggle menu">
          <span className="material-symbols-outlined" style={{ fontSize: 22 }}>menu</span>
        </button>
        <h1 className="topbar-title">{title || t('appTitle')}</h1>
      </div>

      {pipeline && (
        <div className="pipeline-bar">
          {pipeline.map((stage, i) => (
            <div key={stage.key} style={{ display: 'flex', alignItems: 'center' }}>
              <div className={`pipeline-stage ${
                stage.completed ? 'completed' : stage.active ? 'active' : ''
              }`}>
                <span className={`material-symbols-outlined ${
                  stage.active && !stage.completed ? 'animate-pulse' : ''
                }`}>{
                  stage.completed ? 'check_circle' :
                  stage.active ? 'autorenew' :
                  stage.icon
                }</span>
                {stage.label}
              </div>
              {i < pipeline.length - 1 && <span className="pipeline-divider" />}
            </div>
          ))}
        </div>
      )}

      {children || (
        <div className="topbar-status">
          <StatusDot status={systemStatus} />
          {t('localNode')}
        </div>
      )}
    </header>
  )
}
