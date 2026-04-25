import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useLocale } from '../LocaleContext'
import TopBar from '../layouts/TopBar'
import { chatWithDocument } from '../services/api'

export default function SummarizePage() {
  const navigate = useNavigate()
  const { t } = useLocale()
  const [file, setFile] = useState(null)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const onDrop = useCallback((accepted) => {
    if (accepted.length > 0) {
      setFile(accepted[0])
      setResult(null)
      setError(null)
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'image/*': ['.png', '.jpg', '.jpeg', '.tiff'] },
    maxSize: 20 * 1024 * 1024,
    multiple: false,
  })

  const handleSummarize = async () => {
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      // Read file as text for summarization
      const text = await file.text().catch(() => `Document: ${file.name}`)
      const prompt = `Hãy tóm tắt nội dung văn bản hành chính sau đây bằng tiếng Việt, bao gồm: loại văn bản, cơ quan ban hành, ngày ban hành, nội dung chính, và các điểm quan trọng.\n\nVăn bản:\n${text.slice(0, 3000)}`
      const res = await chatWithDocument(prompt, null, text.slice(0, 5000))
      setResult(res.answer)
    } catch (err) {
      setError(err.response?.data?.detail || 'Không thể kết nối LLM. Hãy kiểm tra Ollama.')
    }
    setLoading(false)
  }

  return (
    <>
      <TopBar />
      <div className="page-container" style={{ maxWidth: 800, margin: '0 auto' }}>
        <h1>Quick Summarize</h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: 24, fontSize: 13 }}>
          Upload a document to get an AI-powered summary via Qwen2.5-7B
        </p>

        {/* Dropzone */}
        {!file ? (
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}
            style={{ maxWidth: '100%', padding: '48px 32px' }}>
            <input {...getInputProps()} />
            <span className="material-symbols-outlined" style={{ fontSize: 44, color: 'var(--accent)' }}>upload_file</span>
            <h3 style={{ fontSize: 16, fontWeight: 700, color: 'var(--text-primary)', marginTop: 12 }}>{t('dropTitle')}</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: 13 }}>{t('dropSub')}</p>
          </div>
        ) : (
          <div className="card" style={{ marginBottom: 24 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, background: 'var(--accent-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 20, color: 'var(--accent)' }}>description</span>
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-primary)' }}>{file.name}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{(file.size / 1024).toFixed(0)} KB</div>
                </div>
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-ghost" onClick={() => { setFile(null); setResult(null) }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16 }}>close</span> Remove
                </button>
                <button className="btn btn-primary" onClick={handleSummarize} disabled={loading}>
                  {loading ? (
                    <><span className="material-symbols-outlined spin" style={{ fontSize: 16 }}>autorenew</span> Analyzing...</>
                  ) : (
                    <><span className="material-symbols-outlined" style={{ fontSize: 16 }}>psychology</span> Summarize</>
                  )}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="card" style={{ border: '1px solid rgba(248,113,113,0.3)', background: 'var(--accent-error-muted)', marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 18, color: 'var(--accent-error)' }}>error</span>
              <span style={{ fontSize: 14, color: 'var(--accent-error)', fontWeight: 600 }}>{error}</span>
            </div>
          </div>
        )}

        {/* Result */}
        {result && (
          <div className="card fade-in-up" style={{
            background: 'linear-gradient(135deg, rgba(96,165,250,0.06), rgba(34,211,238,0.04))',
            border: '1px solid rgba(96,165,250,0.15)',
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>lightbulb</span>
              <span style={{ fontSize: 11, fontWeight: 800, color: 'var(--accent)', textTransform: 'uppercase', letterSpacing: 0.5 }}>AI Summary</span>
            </div>
            <div style={{ fontSize: 14, lineHeight: 2, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap' }}>{result}</div>
          </div>
        )}
      </div>
    </>
  )
}
