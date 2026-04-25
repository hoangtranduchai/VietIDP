/** Animated status dot indicator */
export default function StatusDot({ status = 'active', size = 7 }) {
  const colors = {
    active: 'var(--accent-success)',
    inactive: 'var(--accent-error)',
    standby: 'var(--accent-warning)',
    processing: 'var(--accent)',
  }
  const c = colors[status] || colors.standby
  return (
    <span style={{
      display: 'inline-block', width: size, height: size,
      borderRadius: '50%', background: c,
      boxShadow: `0 0 6px ${c}`,
      animation: status === 'active' || status === 'processing'
        ? 'pulse 2s ease-in-out infinite' : 'none',
      flexShrink: 0,
    }} />
  )
}
