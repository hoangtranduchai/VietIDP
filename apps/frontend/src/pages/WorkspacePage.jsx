import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import DocumentViewer from '../components/DocumentViewer'
import ExtractionPanel from '../components/ExtractionPanel'

const API_BASE = 'http://localhost:8000'

const PIPELINE_STAGES = [
  { key: 'input', label: 'Input', icon: 'check_circle' },
  { key: 'ocr', label: 'OCR', icon: 'document_scanner' },
  { key: 'llm', label: 'LLM', icon: 'psychology' },
  { key: 'validation', label: 'Validation', icon: 'fact_check' },
  { key: 'storage', label: 'Storage', icon: 'database' },
]

export default function WorkspacePage() {
  const { id } = useParams()
  const [doc, setDoc] = useState(null)
  const [extraction, setExtraction] = useState({})
  const [processing, setProcessing] = useState(false)
  const [currentStage, setCurrentStage] = useState('input')
  const [processingTime, setProcessingTime] = useState(null)

  useEffect(() => {
    if (id) loadDocument(id)
  }, [id])

  const loadDocument = async (docId) => {
    try {
      const res = await axios.get(`${API_BASE}/api/documents/${docId}`)
      setDoc(res.data)
      if (res.data.extraction) {
        setExtraction(res.data.extraction)
        setCurrentStage('storage')
      }
    } catch (err) {
      console.error('Failed to load document:', err)
    }
  }

  const handleSave = async () => {
    if (!id) return
    try {
      await axios.put(`${API_BASE}/api/documents/${id}`, extraction)
      alert('Đã lưu thành công!')
    } catch (err) {
      alert('Lỗi khi lưu: ' + err.message)
    }
  }

  const handleExport = (format) => {
    if (!id) return
    window.open(`${API_BASE}/api/export/${id}?format=${format}`, '_blank')
  }

  const completedStages = PIPELINE_STAGES.findIndex(s => s.key === currentStage)

  return (
    <>
      {/* TopBar */}
      <header className="topbar">
        <h1 className="topbar-title">NeuralIDP Enterprise</h1>

        {/* Pipeline Status Bar */}
        <div className="pipeline-bar">
          {PIPELINE_STAGES.map((stage, i) => (
            <div key={stage.key}>
              <div className={`pipeline-stage ${
                i < completedStages ? 'completed' :
                i === completedStages ? 'active' : ''
              }`}>
                <span className={`material-symbols-outlined ${
                  i === completedStages && processing ? 'animate-pulse' : ''
                }`}>{
                  i < completedStages ? 'check_circle' :
                  i === completedStages && processing ? 'autorenew' :
                  stage.icon
                }</span>
                {stage.label}
              </div>
              {i < PIPELINE_STAGES.length - 1 && <span className="pipeline-divider" />}
            </div>
          ))}
        </div>

        <div className="topbar-status">
          <span className="topbar-status-dot" />
          Local Node: Active
        </div>
      </header>

      {/* Workspace Actions */}
      <div className="workspace-bar">
        <div>
          <h2>{doc?.filename || 'Select a document'}</h2>
          <p>
            {processingTime ? `Processing time: ${processingTime}s` : ''}
            {extraction?.ocr_confidence ? ` • Confidence: ${Math.round(extraction.ocr_confidence * 100)}%` : ''}
          </p>
        </div>
        <div className="workspace-actions">
          <button className="btn" onClick={() => handleExport('csv')}>
            <span className="material-symbols-outlined">table_view</span>
            Export to Excel
          </button>
          <button className="btn" onClick={handleSave}>
            <span className="material-symbols-outlined">save</span>
            Save to DB
          </button>
          <button className="btn btn-primary" onClick={() => id && loadDocument(id)}>
            <span className="material-symbols-outlined">play_arrow</span>
            Run Validation
          </button>
        </div>
      </div>

      {/* Dual-Pane Viewer */}
      <main className="dual-pane">
        <DocumentViewer
          imageUrl={doc?.file_path ? `${API_BASE}/uploads/${doc.filename}` : null}
          stamps={extraction?.stamp_coordinates || []}
          filename={doc?.filename}
        />
        <ExtractionPanel
          data={extraction}
          onUpdate={setExtraction}
          processing={processing}
        />
      </main>
    </>
  )
}
