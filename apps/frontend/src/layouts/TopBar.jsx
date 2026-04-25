import { useLocale } from '../LocaleContext'
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

  return (
    <header className="topbar">
      <h1 className="topbar-title">{title || t('appTitle')}</h1>

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
          <StatusDot status="active" />
          {t('localNode')}
        </div>
      )}
    </header>
  )
}
