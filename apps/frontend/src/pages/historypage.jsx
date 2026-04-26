import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import { useDocuments } from '../hooks/useDocuments'
import TopBar from '../layouts/TopBar'
import { SkeletonRow } from '../ui/Skeleton'
import EmptyState from '../ui/EmptyState'
import Modal from '../ui/Modal'
import { toast } from 'react-toastify'

export default function HistoryPage() {
  const navigate = useNavigate()
  const { t, locale } = useLocale()
  const { documents, loading, deleteDoc, refresh } = useDocuments()
  const [deleteTarget, setDeleteTarget] = useState(null)

  const handleDelete = async () => {
    if (!deleteTarget) return
    try {
      await deleteDoc(deleteTarget.id)
      toast.success(`Deleted "${deleteTarget.filename}"`)
    } catch {}
    setDeleteTarget(null)
  }

  // Bug 5 fix: Use current locale for date formatting
  const formatDate = (iso) => {
    if (!iso) return ''
    const loc = locale === 'vi' ? 'vi-VN' : 'en-US'
    return new Date(iso).toLocaleString(loc, {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  }
  const formatSize = (bytes) => bytes ? (bytes / 1024).toFixed(0) + ' KB' : ''

  return (
    <>
      <TopBar />
      <div className="page-container">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <h1 style={{ marginBottom: 0 }}>{t('historyTitle')}</h1>
          <button className="btn" onClick={refresh} title={t('refresh')}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>refresh</span>
            {t('refresh')}
          </button>
        </div>

        {loading ? (
          <table className="doc-table">
            <thead><tr><th>{t('colId')}</th><th>{t('colFile')}</th><th>{t('colType')}</th><th>{t('colSize')}</th><th>{t('colStatus')}</th><th>{t('colDate')}</th><th>{t('colActions')}</th></tr></thead>
            <tbody>{[1,2,3,4,5].map(i => <SkeletonRow key={i} cols={7} />)}</tbody>
          </table>
        ) : documents.length === 0 ? (
          <EmptyState
            icon="folder_open"
            title={t('noHistory')}
            subtitle={t('emptyHistorySub')}
            action={<button className="btn btn-primary" onClick={() => navigate('/workspace', { state: { autoOpenUpload: true } })}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span> {t('uploadBtn')}
            </button>}
          />
        ) : (
          <table className="doc-table">
            <thead>
              <tr>
                <th>{t('colId')}</th><th>{t('colFile')}</th><th>{t('colType')}</th>
                <th>{t('colSize')}</th><th>{t('colStatus')}</th><th>{t('colDate')}</th><th>{t('colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {documents.map(doc => (
                <tr key={doc.id}>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 12 }}>#{doc.id}</td>
                  <td>
                    <span style={{ color: 'var(--accent)', cursor: 'pointer', fontWeight: 500 }}
                      onClick={() => navigate(`/workspace/${doc.id}`)}>{doc.filename}</span>
                  </td>
                  <td><span style={{ textTransform: 'uppercase', fontSize: 11, fontFamily: 'var(--font-mono)' }}>{doc.file_type}</span></td>
                  <td>{formatSize(doc.file_size)}</td>
                  <td><span className={`status-badge ${doc.status}`}>{doc.status}</span></td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatDate(doc.created_at)}</td>
                  <td>
                    <div style={{ display: 'flex', gap: 4 }}>
                      <button className="btn" style={{ padding: '4px 8px' }}
                        onClick={() => navigate(`/workspace/${doc.id}`)}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>open_in_new</span>
                      </button>
                      <button className="btn btn-danger" style={{ padding: '4px 8px' }}
                        onClick={() => setDeleteTarget(doc)}>
                        <span className="material-symbols-outlined" style={{ fontSize: 16 }}>delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Delete confirmation modal */}
      <Modal open={!!deleteTarget} onClose={() => setDeleteTarget(null)} title={t('deleteConfirm')} width={420}>
        <p style={{ fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 20 }}>
          {t('deleteConfirmMsg')} <strong style={{ color: 'var(--text-primary)' }}>"{deleteTarget?.filename}"</strong>?
          {' '}{t('deleteUndo')}
        </p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <button className="btn" onClick={() => setDeleteTarget(null)}>{t('deleteCancel')}</button>
          <button className="btn btn-danger" onClick={handleDelete} style={{ background: 'var(--accent-error-muted)' }}>
            <span className="material-symbols-outlined" style={{ fontSize: 16 }}>delete</span> {t('deleteBtn')}
          </button>
        </div>
      </Modal>
    </>
  )
}
