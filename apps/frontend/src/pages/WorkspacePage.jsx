import { useState, useEffect, useCallback, useRef } from 'react'
import { useParams, useNavigate, useLocation } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useLocale } from '../LocaleContext'
import { useApi } from '../hooks/useApi'
import { getDocument, updateDocument, getExportUrl, processDocument } from '../services/api'
import api from '../services/api'
import TopBar from '../layouts/TopBar'
import DocumentViewer from '../components/DocumentViewer'
import ChatPanel from '../components/ChatPanel'
import ExtractionPanel from '../components/ExtractionPanel'
import OverviewPanel from '../components/OverviewPanel'
import Skeleton from '../ui/Skeleton'
import { toast } from 'react-toastify'

const PIPELINE = ['YOLOv8', 'VietOCR', 'Qwen2.5-7B', 'JSON']

export default function WorkspacePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useLocale()
  const docApi = useApi(getDocument)
  const [extraction, setExtraction] = useState({})
  const [currentStage, setCurrentStage] = useState('input')
  const [activeTab, setActiveTab] = useState('overview') // 'overview' | 'extraction' | 'chat'
  const [hasUnreadChat, setHasUnreadChat] = useState(false)
  const [highlightBboxes, setHighlightBboxes] = useState(null)
  
  const [leftWidth, setLeftWidth] = useState(50)
  const [isDragging, setIsDragging] = useState(false)
  const [rightCollapsed, setRightCollapsed] = useState(false)
  
  const uploadDialogOpened = useRef(false)
  const dualPaneRef = useRef(null)

  const handleMouseMove = useCallback((e) => {
    if (!isDragging || !dualPaneRef.current) return;
    const rect = dualPaneRef.current.getBoundingClientRect();
    const offset = e.clientX - rect.left;
    const newLeftWidth = (offset / rect.width) * 100;
    if (newLeftWidth > 20 && newLeftWidth < 80) {
      setLeftWidth(newLeftWidth);
    }
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = 'none';
      document.body.style.cursor = 'col-resize';
    } else {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    }
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      document.body.style.userSelect = '';
      document.body.style.cursor = '';
    };
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Upload state
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  const PIPELINE_STAGES = [
    { key: 'input', label: t('stInput'), icon: 'check_circle' },
    { key: 'ocr', label: t('stOCR'), icon: 'document_scanner' },
    { key: 'llm', label: t('stLLM'), icon: 'psychology' },
    { key: 'validation', label: t('stValidation'), icon: 'fact_check' },
    { key: 'storage', label: t('stStorage'), icon: 'database' },
  ]

  useEffect(() => {
    if (!id) {
      // Clear data if we navigate to /workspace (Empty state)
      setExtraction({})
      return
    }
    const controller = new AbortController()

    docApi.execute(id).then(doc => {
      if (controller.signal.aborted) return
      if (doc?.extraction) {
        setExtraction(doc.extraction)
        setCurrentStage('storage')
        if (doc.extraction.trich_yeu) setHasUnreadChat(true)
      }
    }).catch(() => {})

    return () => controller.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id, docApi.execute])

  const handleSave = async () => {
    if (!id) return
    try {
      await updateDocument(id, extraction)
    } catch {}
  }

  const handleExport = (format) => {
    if (!id) return
    window.open(getExportUrl(id, format), '_blank')
  }

  const completedIdx = PIPELINE_STAGES.findIndex(s => s.key === currentStage)
  const pipeline = PIPELINE_STAGES.map((s, i) => ({
    ...s,
    completed: i < completedIdx,
    active: i === completedIdx,
  }))

  const doc = docApi.data

  const imageUrl = doc?.storage_name
    ? `${api.defaults.baseURL}/uploads/${doc.storage_name}`
    : null

  const pageUrls = extraction?.raw_json?.pages 
    ? extraction.raw_json.pages.map(p => `${api.defaults.baseURL}/uploads/${p}`)
    : []

  // ── Drag & Drop Logic ──────────────────────────────────────────
  const onDrop = useCallback(async (files) => {
    if (files.length === 0) return
    setUploading(true)
    setProgress(10)

    try {
      setProgress(30)
      const res = await processDocument(files[0], (e) => {
        const pct = Math.round((e.loaded / e.total) * 70) + 30
        setProgress(pct)
      })
      setProgress(100)
      if (res.task_id) {
        navigate(`/processing/${res.task_id}?docId=${res.document_id}`, { state: { filename: files[0].name } })
      } else if (res.document_id) {
        toast.success('Processing complete!')
        navigate(`/workspace/${res.document_id}`)
      }
    } catch {
      // Error handled by interceptor
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }, [navigate])

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    noClick: true, // Always disable global click to prevent TopBar from opening file picker
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
    },
    maxSize: 20 * 1024 * 1024,
    multiple: false,
  })

  // Handle auto-open upload dialog from SideNavBar or HistoryPage
  useEffect(() => {
    if (location.state?.autoOpenUpload && !id && !uploading && open && !uploadDialogOpened.current) {
      uploadDialogOpened.current = true
      open()
      // Clear the state so it doesn't reopen on reload, and pass an empty state object!
      navigate('/workspace', { replace: true, state: {} })
      
      // Reset the ref after a delay in case they want to click it again later
      setTimeout(() => { uploadDialogOpened.current = false }, 1000)
    }
  }, [location.state, id, uploading, open, navigate])

  // Render Uploading Overlay or Empty State Dropzone
  if (!id || uploading) {
    return (
      <div {...getRootProps()} style={{ height: '100%', outline: 'none' }}>
        <input {...getInputProps()} />
        <TopBar />
        <div className={`upload-page ${isDragActive ? 'active' : ''}`} style={id ? { position: 'absolute', inset: 0, zIndex: 100, background: 'var(--bg-primary)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' } : {}}>
          {uploading ? (
            <div style={{ textAlign: 'center', animation: 'fadeIn 0.4s ease' }}>
              <span className="material-symbols-outlined spin" style={{
                fontSize: 56, color: 'var(--accent)', filter: 'drop-shadow(0 0 20px rgba(96,165,250,0.4))'
              }}>autorenew</span>
              <h3 style={{ fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700, color: 'var(--text-primary)', margin: '20px 0 8px' }}>
                Uploading Document...
              </h3>
              <p style={{ color: 'var(--text-muted)', marginBottom: 24, fontSize: 13 }}>Please wait while your document is uploaded securely.</p>
              
              <div className="progress-bar" style={{ width: 400, margin: '0 auto' }}>
                <div className="progress-fill" style={{ width: `${progress}%` }} />
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8 }}>{progress}%</p>

              <div style={{ display: 'flex', justifyContent: 'center', gap: 12, marginTop: 28, flexWrap: 'wrap' }}>
                {PIPELINE.map((stage, i) => {
                  const done = progress > (i + 1) * 22
                  const active = !done && progress > i * 22
                  return (
                    <div key={stage} style={{
                      display: 'flex', alignItems: 'center', gap: 6, padding: '6px 14px', borderRadius: 'var(--radius-full)',
                      background: done ? 'var(--accent-success-muted)' : active ? 'var(--accent-muted)' : 'rgba(255,255,255,0.03)',
                      border: `1px solid ${done ? 'rgba(52,211,153,0.2)' : active ? 'rgba(96,165,250,0.2)' : 'var(--border)'}`,
                      fontSize: 11, fontWeight: 600, color: done ? 'var(--accent-success)' : active ? 'var(--accent)' : 'var(--text-muted)',
                      transition: 'all 0.3s',
                    }}>
                      <span className="material-symbols-outlined" style={{ fontSize: 14 }}>
                        {done ? 'check_circle' : active ? 'autorenew' : 'radio_button_unchecked'}
                      </span>
                      {stage}
                    </div>
                  )
                })}
              </div>
            </div>
          ) : (
            <div className={`dropzone ${isDragActive ? 'active' : ''}`} style={id ? { border: '4px dashed var(--accent)', margin: 40, cursor: 'pointer' } : { cursor: 'pointer' }} onClick={open}>
              <span className="material-symbols-outlined">cloud_upload</span>
              <h3>{t('dropTitle')}</h3>
              <p>{t('dropSub')}</p>

              <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 16, flexWrap: 'wrap' }}>
                {['PDF', 'PNG', 'JPG', 'TIFF'].map(fmt => (
                  <span key={fmt} className="badge badge-blue">{fmt}</span>
                ))}
              </div>

              <div style={{
                display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 20, padding: '14px 14px', borderRadius: 'var(--radius-full)',
                background: 'var(--accent-success-muted)', border: '1px solid rgba(52,211,153,0.15)',
                fontSize: 11, color: 'var(--accent-success)', fontWeight: 600,
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14 }}>lock</span>
                {t('dropSecurity')}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div {...getRootProps()} style={{ height: '100%', outline: 'none', position: 'relative', display: 'flex', flexDirection: 'column' }}>
      <input {...getInputProps()} />
      
      {/* Global Drag Overlay when a document is open */}
      {isDragActive && (
        <div style={{
          position: 'absolute', inset: 0, zIndex: 1000, background: 'rgba(0,0,0,0.8)',
          backdropFilter: 'blur(8px)', display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '4px dashed var(--accent)', borderRadius: 'var(--radius)'
        }}>
          <div style={{ textAlign: 'center', color: 'white' }}>
            <span className="material-symbols-outlined float" style={{ fontSize: 80, color: 'var(--accent)' }}>upload_file</span>
            <h2 style={{ fontSize: 32, marginTop: 20, fontFamily: 'var(--font-display)' }}>Drop to Replace Document</h2>
          </div>
        </div>
      )}

      <TopBar pipeline={pipeline} />

      <div className="workspace-bar">
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          {extraction?.loai_van_ban && (
            <div className="ws-doc-badge">
              <span className="material-symbols-outlined" style={{ fontSize: 15, color: 'var(--accent)' }}>description</span>
              <span>{extraction.loai_van_ban}{extraction.so_hieu ? ` · ${extraction.so_hieu}` : ''}</span>
            </div>
          )}
          <div>
            <h2>{doc?.filename || t('selectDoc')}</h2>
            <div className="ws-mini-stats">
              {extraction?.processing_time && (
                <span className="ws-stat-chip">
                  <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--accent-cyan)' }}>timer</span>
                  {extraction.processing_time}s
                </span>
              )}
              {extraction?.ocr_confidence && (
                <span className="ws-stat-chip">
                  <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--accent-success)' }}>verified</span>
                  {Math.round(extraction.ocr_confidence * 100)}%
                </span>
              )}
              {extraction?.total_stamps > 0 && (
                <span className="ws-stat-chip">
                  <span className="material-symbols-outlined" style={{ fontSize: 12, color: 'var(--accent-error)' }}>stamp</span>
                  {extraction.total_stamps}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="workspace-actions">
          <button className="btn" onClick={() => navigate('/workspace', { state: { autoOpenUpload: true } })}>
            <span className="material-symbols-outlined">add_circle</span>
            {t('uploadNew')}
          </button>
          <button className="btn" onClick={() => handleExport('csv')}>
            <span className="material-symbols-outlined">table_view</span>
            {t('exportExcel')}
          </button>
          <button className="btn" onClick={() => { handleSave(); toast.success('Đã lưu chỉnh sửa thành công!'); }}>
            <span className="material-symbols-outlined">save</span>
            {t('saveEdits')}
          </button>
          <button className="btn btn-primary" onClick={() => id && docApi.execute(id)}>
            <span className="material-symbols-outlined">play_arrow</span>
            {t('runValidation')}
          </button>
        </div>
      </div>

      <main className={`dual-pane ${rightCollapsed ? 'right-collapsed' : ''}`} ref={dualPaneRef}>
        {docApi.loading ? (
          <>
            <div className="pane pane-source"><div style={{ padding: 32 }}><Skeleton variant="card" height={500} /></div></div>
            <div className="pane pane-extraction"><div style={{ padding: 20 }}><Skeleton rows={6} style={{ marginBottom: 16 }} /></div></div>
          </>
        ) : (
          <>
            <DocumentViewer
              imageUrl={imageUrl}
              stamps={extraction?.stamp_coordinates || []}
              highlightBboxes={highlightBboxes}
              filename={doc?.filename}
              pages={pageUrls}
              style={{ width: rightCollapsed ? '100%' : `calc(${leftWidth}% - 10px)`, flex: 'none' }}
              onToggleCollapse={() => setRightCollapsed(!rightCollapsed)}
              isCollapsed={rightCollapsed}
            />

            {!rightCollapsed && (
              <>
                <div 
                  className="splitter"
                  onMouseDown={() => setIsDragging(true)}
                  style={{ 
                    width: 20, margin: '0 -10px', zIndex: 10, cursor: 'col-resize',
                    display: 'flex', alignItems: 'center', justifyContent: 'center'
                  }}
                  title="Kéo để thay đổi kích thước"
                >
                  <div style={{ 
                    width: 14, height: 48, borderRadius: 8, 
                    background: isDragging ? 'var(--accent)' : 'var(--bg-elevated)', 
                    border: isDragging ? 'none' : '1px solid var(--glass-border)',
                    boxShadow: 'var(--shadow-md)',
                    transition: 'all 0.2s var(--ease)', display: 'flex', justifyContent: 'center', alignItems: 'center'
                  }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 14, color: isDragging ? 'white' : 'var(--text-muted)' }}>drag_indicator</span>
                  </div>
                </div>

                <div className="pane pane-extraction" style={{ width: `calc(${100 - leftWidth}% - 10px)`, flex: 'none', display: 'flex', flexDirection: 'column' }}>
              <div className="workspace-tabs">
                <button 
                  className={`workspace-tab ${activeTab === 'overview' ? 'active' : ''}`}
                  onClick={() => setActiveTab('overview')}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>dashboard</span>
                  {t('tabOverview')}
                </button>
                <button 
                  className={`workspace-tab ${activeTab === 'extraction' ? 'active' : ''}`}
                  onClick={() => setActiveTab('extraction')}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>data_object</span>
                  {t('tabExtraction')}
                </button>
                <button 
                  className={`workspace-tab ${activeTab === 'chat' ? 'active' : ''}`}
                  onClick={() => { setActiveTab('chat'); setHasUnreadChat(false); }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>forum</span>
                  {t('tabChat')}
                  {hasUnreadChat && activeTab !== 'chat' && (
                    <span className="ws-unread-dot" />
                  )}
                </button>
              </div>
              
              <div style={{ display: activeTab === 'overview' ? 'flex' : 'none', flex: 1, overflow: 'hidden', flexDirection: 'column', minHeight: 0 }}>
                <OverviewPanel data={extraction} />
              </div>
              <div style={{ display: activeTab === 'extraction' ? 'flex' : 'none', flex: 1, overflow: 'hidden', flexDirection: 'column', minHeight: 0 }}>
                <ExtractionPanel
                  data={extraction}
                  onUpdate={setExtraction}
                  processing={docApi.loading}
                  onFocusField={setHighlightBboxes}
                />
              </div>
              <div style={{ display: activeTab === 'chat' ? 'flex' : 'none', flex: 1, overflow: 'hidden', flexDirection: 'column', minHeight: 0 }}>
                <ChatPanel documentId={parseInt(id)} context={extraction?.full_text} />
              </div>
            </div>
            </>
            )}
          </>
        )}
      </main>
    </div>
  )
}
