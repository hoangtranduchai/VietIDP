/**
 * Reusable Empty State
 * Shows icon, title, subtitle for empty lists/pages
 */
export default function EmptyState({ icon = 'folder_open', title, subtitle, action }) {
  return (
    <div className="empty-state fade-in">
      <span className="material-symbols-outlined" style={{
        fontSize: 64, color: 'var(--text-muted)', opacity: 0.25,
        marginBottom: 16,
      }}>{icon}</span>
      <h3 style={{
        fontSize: 16, fontWeight: 600, color: 'var(--text-secondary)',
        marginBottom: 6,
      }}>{title}</h3>
      {subtitle && (
        <p style={{ fontSize: 13, color: 'var(--text-muted)', maxWidth: 320, lineHeight: 1.6 }}>
          {subtitle}
        </p>
      )}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  )
}
