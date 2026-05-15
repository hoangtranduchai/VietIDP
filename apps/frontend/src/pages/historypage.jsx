import { useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import { useDocuments } from '../hooks/useDocuments'
import TopBar from '../layouts/TopBar'
import { SkeletonRow } from '../ui/Skeleton'
import EmptyState from '../ui/EmptyState'
import Modal from '../ui/Modal'
import { toast } from 'react-toastify'
import { MOCK_DOCUMENTS } from '../data/mockData'

export default function HistoryPage() {
  const navigate = useNavigate()
  const { t, locale } = useLocale()
  const { documents: realDocs, loading, error, deleteDoc, refresh } = useDocuments()
  const [deleteTarget, setDeleteTarget] = useState(null)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('all')
  const [filterType, setFilterType] = useState('all')

  // Use mock data if backend is unavailable
  const documents = (!loading && (error || realDocs.length === 0)) ? MOCK_DOCUMENTS : realDocs
  const isMock = documents === MOCK_DOCUMENTS

  // Filtering
  const filtered = useMemo(() => {
    let result = documents
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(d =>
        d.filename?.toLowerCase().includes(q) ||
        d.extraction?.loai_van_ban?.toLowerCase().includes(q) ||
        d.extraction?.so_hieu?.toLowerCase().includes(q) ||
        d.extraction?.co_quan_ban_hanh?.toLowerCase().includes(q)
      )
    }
    if (filterStatus !== 'all') {
      result = result.filter(d => d.status === filterStatus)
    }
    if (filterType !== 'all') {
      result = result.filter(d => d.file_type === filterType)
    }
    return result
  }, [documents, search, filterStatus, filterType])

  const handleDelete = async () => {
    if (!deleteTarget) return
    if (isMock) {
      toast.info('Demo mode — delete disabled')
      setDeleteTarget(null)
      return
    }
    try {
      await deleteDoc(deleteTarget.id)
      toast.success(`Deleted "${deleteTarget.filename}"`)
    } catch {}
    setDeleteTarget(null)
  }

  const formatDate = (iso) => {
    if (!iso) return ''
    const loc = locale === 'vi' ? 'vi-VN' : 'en-US'
    return new Date(iso).toLocaleString(loc, {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  }
  const formatSize = (bytes) => bytes ? (bytes / 1024).toFixed(0) + ' KB' : ''

  // Extract unique file types for filter
  const fileTypes = [...new Set(documents.map(d => d.file_type).filter(Boolean))]

  const statusCounts = {
    all: documents.length,
    completed: documents.filter(d => d.status === 'completed').length,
    processing: documents.filter(d => d.status === 'processing').length,
    failed: documents.filter(d => d.status === 'failed').length,
  }

  return (
    <>
      <TopBar />
      <div className="page-container">
        {/* Header Row */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
          <div>
            <h1 style={{ marginBottom: 4 }}>{t('historyTitle')}</h1>
            {isMock && (
              <span className="badge badge-yellow" style={{ fontSize: 10 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 12 }}>info</span>
                Demo Mode
              </span>
            )}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn" onClick={refresh} title={t('refresh')}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>refresh</span>
              {t('refresh')}
            </button>
            <button className="btn btn-primary" onClick={() => navigate('/workspace', { state: { autoOpenUpload: true } })}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span>
              {t('uploadBtn')}
            </button>
          </div>
        </div>

        {/* Search & Filters Row */}
        <div className="history-filters" style={{
          display: 'flex', gap: 10, marginBottom: 20, flexWrap: 'wrap', alignItems: 'center',
        }}>
          {/* Search */}
          <div style={{
            flex: '1 1 260px', maxWidth: 360, position: 'relative',
          }}>
            <span className="material-symbols-outlined" style={{
              position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)',
              fontSize: 18, color: 'var(--text-muted)',
            }}>search</span>
            <input
              type="text" value={search} onChange={e => setSearch(e.target.value)}
              placeholder={locale === 'vi' ? 'Tìm theo tên file, loại VB, số hiệu...' : 'Search by filename, type, ID...'}
              style={{
                width: '100%', padding: '10px 12px 10px 40px',
                borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
                background: 'var(--bg-primary)', color: 'var(--text-primary)',
                fontFamily: 'var(--font)', fontSize: 13, outline: 'none',
                transition: 'border-color 0.2s',
              }}
              onFocus={e => e.target.style.borderColor = 'var(--accent)'}
              onBlur={e => e.target.style.borderColor = 'var(--border)'}
            />
          </div>

          {/* Status Filter */}
          <div style={{ display: 'flex', gap: 4 }}>
            {['all', 'completed', 'processing', 'failed'].map(status => (
              <button key={status} onClick={() => setFilterStatus(status)}
                className={`btn ${filterStatus === status ? 'btn-primary' : ''}`}
                style={{ padding: '6px 14px', fontSize: 12 }}>
                {status === 'all' ? (locale === 'vi' ? 'Tất cả' : 'All') : status}
                <span style={{
                  marginLeft: 4, fontSize: 10, fontFamily: 'var(--font-mono)',
                  opacity: 0.7,
                }}>
                  {statusCounts[status]}
                </span>
              </button>
            ))}
          </div>

          {/* Type Filter */}
          <select
            value={filterType} onChange={e => setFilterType(e.target.value)}
            style={{
              padding: '8px 12px', borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--border)', background: 'var(--bg-primary)',
              color: 'var(--text-primary)', fontFamily: 'var(--font)', fontSize: 12,
              cursor: 'pointer',
            }}
          >
            <option value="all">{locale === 'vi' ? 'Loại file' : 'File type'}</option>
            {fileTypes.map(ft => <option key={ft} value={ft}>{ft.toUpperCase()}</option>)}
          </select>
        </div>

        {/* Results count */}
        <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 12 }}>
          {filtered.length} / {documents.length} {locale === 'vi' ? 'văn bản' : 'documents'}
          {search && ` — "${search}"`}
        </div>

        {loading ? (
          <div style={{ overflowX: 'auto', width: '100%' }}>
            <table className="doc-table" style={{ minWidth: 800 }}>
              <thead><tr><th>{t('colId')}</th><th>{t('colFile')}</th><th>{t('colType')}</th><th>{t('colSize')}</th><th>{t('colStatus')}</th><th>{t('colDate')}</th><th>{t('colActions')}</th></tr></thead>
              <tbody>{[1,2,3,4,5].map(i => <SkeletonRow key={i} cols={7} />)}</tbody>
            </table>
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState
            icon="folder_open"
            title={search ? (locale === 'vi' ? 'Không tìm thấy kết quả' : 'No results found') : t('noHistory')}
            subtitle={search ? (locale === 'vi' ? 'Thử từ khóa khác' : 'Try a different search') : t('emptyHistorySub')}
            action={!search && <button className="btn btn-primary" onClick={() => navigate('/workspace', { state: { autoOpenUpload: true } })}>
              <span className="material-symbols-outlined" style={{ fontSize: 16 }}>add</span> {t('uploadBtn')}
            </button>}
          />
        ) : (
          <div style={{ overflowX: 'auto', width: '100%' }}>
            <table className="doc-table" style={{ minWidth: 800 }}>
              <thead>
              <tr>
                <th>{t('colId')}</th><th>{t('colFile')}</th><th style={{ textAlign: 'center' }}>{t('colType')}</th>
                <th>{t('colSize')}</th><th style={{ textAlign: 'center' }}>{t('colPages')}</th>
                <th style={{ textAlign: 'center' }}>{t('colStatus')}</th><th>{t('colDate')}</th><th>{t('colActions')}</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map(doc => (
                <tr key={doc.id} style={{ cursor: 'pointer' }} onClick={() => navigate(`/workspace/${doc.id}`)}>
                  <td style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-muted)', fontSize: 12 }}>#{doc.id}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                      <div style={{
                        width: 32, height: 32, borderRadius: 8,
                        background: doc.file_type === 'pdf' ? 'var(--accent-error-muted)' : 'var(--accent-muted)',
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                      }}>
                        <span className="material-symbols-outlined" style={{
                          fontSize: 16,
                          color: doc.file_type === 'pdf' ? 'var(--accent-error)' : 'var(--accent)',
                        }}>{doc.file_type === 'pdf' ? 'picture_as_pdf' : 'image'}</span>
                      </div>
                      <div>
                        <div style={{ fontWeight: 600, color: 'var(--accent)', fontSize: 13 }}>{doc.filename}</div>
                        {doc.extraction?.loai_van_ban && (
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                            {doc.extraction.loai_van_ban}{doc.extraction.so_hieu ? ` · ${doc.extraction.so_hieu}` : ''}
                          </div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span className={`badge ${doc.file_type === 'pdf' ? 'badge-red' : 'badge-blue'}`}>
                      {doc.file_type?.toUpperCase()}
                    </span>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {formatSize(doc.file_size)}
                  </td>
                  <td style={{ textAlign: 'center', fontSize: 12, fontFamily: 'var(--font-mono)' }}>
                    {doc.num_pages || '—'}
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <span className={`status-badge ${doc.status}`}>{doc.status}</span>
                  </td>
                  <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>{formatDate(doc.created_at)}</td>
                  <td onClick={e => e.stopPropagation()}>
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
          </div>
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
