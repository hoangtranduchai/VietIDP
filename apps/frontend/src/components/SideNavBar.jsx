import { NavLink, useNavigate } from 'react-router-dom'

const navItems = [
  { path: '/', icon: 'move_to_inbox', label: 'Ingestion' },
  { path: '/workspace', icon: 'document_scanner', label: 'OCR Extraction' },
  { path: '/chat', icon: 'psychology', label: 'Neural Parsing' },
  { path: '/history', icon: 'fact_check', label: 'Validation' },
  { path: '/export', icon: 'ios_share', label: 'Export' },
]

const footerItems = [
  { path: '/dashboard', icon: 'analytics', label: 'System Health' },
]

export default function SideNavBar() {
  const navigate = useNavigate()

  return (
    <nav className="sidenav">
      {/* Brand */}
      <div className="sidenav-brand">
        <div className="sidenav-brand-icon">AI</div>
        <div>
          <h2>IDP Console</h2>
          <p>Secure Govt-Cloud</p>
        </div>
      </div>

      {/* Upload Button */}
      <button className="sidenav-upload-btn" onClick={() => navigate('/')}>
        <span className="material-symbols-outlined" style={{fontSize: 18}}>add</span>
        Upload Document
      </button>

      {/* Navigation Links */}
      <div className="sidenav-links">
        {navItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({isActive}) => `sidenav-link ${isActive ? 'active' : ''}`}
            end={item.path === '/'}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </div>

      {/* Footer Links */}
      <div className="sidenav-footer">
        {footerItems.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({isActive}) => `sidenav-link ${isActive ? 'active' : ''}`}
          >
            <span className="material-symbols-outlined">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  )
}
