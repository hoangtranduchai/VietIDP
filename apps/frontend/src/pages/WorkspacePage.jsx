import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import { useApi } from '../hooks/useApi'
import { getDocument, updateDocument, getExportUrl } from '../services/api'
import TopBar from '../layouts/TopBar'
import DocumentViewer from '../components/DocumentViewer'
import ExtractionPanel from '../components/ExtractionPanel'
import Skeleton from '../ui/Skeleton'
import { toast } from 'react-toastify'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function WorkspacePage() {
  const { id } = useParams()
  const { t } = useLocale()
  const docApi = useApi(getDocument)
  const [extraction, setExtraction] = useState({})
  const [currentStage, setCurrentStage] = useState('input')

  const PIPELINE_STAGES = [
    { key: 'input', label: t('stInput'), icon: 'check_circle' },
    { key: 'ocr', label: t('stOCR'), icon: 'document_scanner' },
    { key: 'llm', label: t('stLLM'), icon: 'psychology' },
    { key: 'validation', label: t('stValidation'), icon: 'fact_check' },
    { key: 'storage', label: t('stStorage'), icon: 'database' },
  ]

  useEffect(() => {
    if (id) {
      docApi.execute(id).then(doc => {
        if (doc?.extraction) {
          setExtraction(doc.extraction)
          setCurrentStage('storage')
        }
      }).catch(() => {})
    }
  }, [id])

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

  return (
    <>
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
              imageUrl={doc?.file_path ? `${API_BASE}/uploads/${doc.filename}` : null}
              stamps={extraction?.stamp_coordinates || []}
              filename={doc?.filename}
            />
            <ExtractionPanel
              data={extraction}
              onUpdate={setExtraction}
              processing={docApi.loading}
            />
          </>
        )}
      </main>
    </>
  )
}
