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
  const [activeTab, setActiveTab] = useState('extraction') // 'extraction' | 'chat'
  const [hasUnreadChat, setHasUnreadChat] = useState(false)
  
  const uploadDialogOpened = useRef(false)

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

  const imageUrl = doc?.file_path
    ? `${api.defaults.baseURL}/uploads/${doc.filename}`
    : null

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
        navigate(`/processing/${res.task_id}?docId=${res.document_id}`)
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
                display: 'inline-flex', alignItems: 'center', gap: 6, marginTop: 20, padding: '6px 14px', borderRadius: 'var(--radius-full)',
                background: 'var(--accent-success-muted)', border: '1px solid rgba(52,211,153,0.15)',
                fontSize: 11, color: 'var(--accent-success)', fontWeight: 600,
              }}>
                <span className="material-symbols-outlined" style={{ fontSize: 14, transform: 'translateY(-1px)' }}>lock</span>
                {t('dropSecurity')}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div {...getRootProps()} style={{ height: '100%', outline: 'none', position: 'relative' }}>
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
        <div>
          <h2>{doc?.filename || t('selectDoc')}</h2>
          <p>
            {extraction?.processing_time ? `${extraction.processing_time}s` : ''}
            {extraction?.ocr_confidence ? ` • ${Math.round(extraction.ocr_confidence * 100)}%` : ''}
          </p>
        </div>
        <div className="workspace-actions">
          <button className="btn" onClick={() => handleExport('csv')}>
            <span className="material-symbols-outlined">table_view</span>
            {t('exportExcel')}
          </button>
          <button className="btn" onClick={handleSave}>
            <span className="material-symbols-outlined">save</span>
            {t('saveToDB')}
          </button>
          <button className="btn btn-primary" onClick={() => id && docApi.execute(id)}>
            <span className="material-symbols-outlined">play_arrow</span>
            {t('runValidation')}
          </button>
        </div>
      </div>

      <main className="dual-pane">
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
              filename={doc?.filename}
            />
            <div className="pane pane-extraction" style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', background: 'var(--bg-elevated)', flexShrink: 0 }}>
                <button 
                  style={{ flex: 1, padding: '12px', border: 'none', background: activeTab === 'extraction' ? 'var(--bg-card)' : 'transparent', color: activeTab === 'extraction' ? 'var(--text-primary)' : 'var(--text-muted)', borderBottom: activeTab === 'extraction' ? '2px solid var(--accent)' : '2px solid transparent', cursor: 'pointer', fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6 }}
                  onClick={() => setActiveTab('extraction')}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>data_object</span>
                  Extraction
                </button>
                <button 
                  style={{ flex: 1, padding: '12px', border: 'none', background: activeTab === 'chat' ? 'var(--bg-card)' : 'transparent', color: activeTab === 'chat' ? 'var(--text-primary)' : 'var(--text-muted)', borderBottom: activeTab === 'chat' ? '2px solid var(--accent)' : '2px solid transparent', cursor: 'pointer', fontWeight: 600, fontSize: 13, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6, position: 'relative' }}
                  onClick={() => { setActiveTab('chat'); setHasUnreadChat(false); }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>forum</span>
                  Chat / Summarize
                  {hasUnreadChat && activeTab !== 'chat' && (
                    <span style={{ position: 'absolute', top: 10, right: 10, width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-error)', boxShadow: '0 0 6px var(--accent-error)' }} />
                  )}
                </button>
              </div>
              
              <div style={{ display: activeTab === 'extraction' ? 'flex' : 'none', flex: 1, overflow: 'hidden', flexDirection: 'column' }}>
                <ExtractionPanel
                  data={extraction}
                  onUpdate={setExtraction}
                  processing={docApi.loading}
                />
              </div>
              <div style={{ display: activeTab === 'chat' ? 'flex' : 'none', flex: 1, overflow: 'hidden', flexDirection: 'column' }}>
                <ChatPanel documentId={parseInt(id)} context={extraction?.full_text} />
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  )
}
