import { useNavigate } from 'react-router-dom'
import { useLocale } from '../LocaleContext'

/**
 * 404 Not Found page
 * Shown when the user navigates to a non-existent route
 */
export default function NotFoundPage() {
  const navigate = useNavigate()
  const { locale } = useLocale()

  const isVi = locale === 'vi'

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      justifyContent: 'center', height: '100vh', textAlign: 'center',
      padding: 32, gap: 12,
    }}>
      <span className="material-symbols-outlined" style={{
        fontSize: 72, color: 'var(--text-muted)', opacity: 0.2, marginBottom: 8,
      }}>explore_off</span>
      <h1 style={{
        fontSize: 56, fontWeight: 900, color: 'var(--text-primary)',
        fontFamily: 'var(--font-display)', lineHeight: 1,
      }}>404</h1>
      <p style={{
        fontSize: 16, color: 'var(--text-muted)', maxWidth: 360, lineHeight: 1.6,
      }}>
        {isVi
          ? 'Trang bạn tìm kiếm không tồn tại.'
          : "The page you're looking for doesn't exist."}
      </p>
      <button className="btn btn-primary" onClick={() => navigate('/')} style={{ marginTop: 12 }}>
        <span className="material-symbols-outlined" style={{ fontSize: 18 }}>home</span>
        {isVi ? 'Về trang chủ' : 'Go Home'}
      </button>
    </div>
  )
}
