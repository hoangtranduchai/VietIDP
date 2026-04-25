/**
 * Shimmer Skeleton Loader
 * Variants: text, card, circle, bar
 */
export default function Skeleton({ width, height, variant = 'text', rows = 1, style }) {
  const base = {
    background: 'linear-gradient(90deg, rgba(255,255,255,0.03) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.03) 75%)',
    backgroundSize: '200% 100%',
    animation: 'shimmer 1.8s ease-in-out infinite',
    borderRadius: variant === 'circle' ? '50%' : variant === 'card' ? 'var(--radius)' : '6px',
  }

  if (variant === 'card') {
    return (
      <div className="skeleton-card" style={{
        ...base, width: width || '100%', height: height || 120,
        border: '1px solid var(--border)', ...style,
      }} />
    )
  }

  if (variant === 'circle') {
    const size = width || 40
    return <div style={{ ...base, width: size, height: size, flexShrink: 0, ...style }} />
  }

  // Text variant — render multiple rows
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8, ...style }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{
          ...base,
          width: i === rows - 1 && rows > 1 ? '60%' : (width || '100%'),
          height: height || 14,
        }} />
      ))}
    </div>
  )
}

/** Skeleton row for tables */
export function SkeletonRow({ cols = 6 }) {
  return (
    <tr>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} style={{ padding: '14px 16px' }}>
          <Skeleton width={i === 0 ? 40 : i === cols - 1 ? 60 : '80%'} />
        </td>
      ))}
    </tr>
  )
}
