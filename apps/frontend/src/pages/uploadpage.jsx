import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { useLocale } from '../LocaleContext'
import TopBar from '../layouts/TopBar'
import { processDocument } from '../services/api'
import { toast } from 'react-toastify'

const PIPELINE = ['YOLOv8', 'VietOCR', 'Qwen2.5-7B', 'JSON']

export default function UploadPage() {
  const navigate = useNavigate()
  const { t } = useLocale()
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  const onDrop = useCallback(async (files) => {
    if (files.length === 0) return
    setUploading(true)
    setProgress(10)

    try {
      setProgress(30)
      const res = await processDocument(files[0], (e) => {
        const pct = Math.round((e.loaded / e.total) * 40) + 30
        setProgress(pct)
      })
      setProgress(100)
      toast.success('Processing complete!')
      if (res.document_id) {
        navigate(`/workspace/${res.document_id}`)
      }
    } catch {
      // Error handled by API interceptor toast
    } finally {
      setUploading(false)
      setProgress(0)
    }
  }, [navigate])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/*': ['.png', '.jpg', '.jpeg', '.tiff', '.bmp'],
    },
    maxSize: 20 * 1024 * 1024,
    multiple: false,
  })

  return (
    <>
      <TopBar />

      <div className="upload-page">
        {uploading ? (
          <div style={{ textAlign: 'center', animation: 'fadeIn 0.4s ease' }}>
            <span className="material-symbols-outlined spin" style={{
              fontSize: 56, color: 'var(--accent)',
              filter: 'drop-shadow(0 0 20px rgba(96,165,250,0.4))'
            }}>autorenew</span>
            <h3 style={{
              fontFamily: 'var(--font-display)', fontSize: 22, fontWeight: 700,
              color: 'var(--text-primary)', margin: '20px 0 8px'
            }}>
              {t('processing')}
            </h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: 24, fontSize: 13 }}>
              {t('pipelineRun')}
            </p>

            {/* Progress bar */}
            <div className="progress-bar" style={{ width: 400, margin: '0 auto' }}>
              <div className="progress-fill" style={{ width: `${progress}%` }} />
            </div>
            <p style={{ color: 'var(--text-muted)', fontSize: 12, marginTop: 8 }}>{progress}%</p>

            {/* Pipeline stages */}
            <div style={{
              display: 'flex', justifyContent: 'center', gap: 12,
              marginTop: 28, flexWrap: 'wrap'
            }}>
              {PIPELINE.map((stage, i) => {
                const done = progress > (i + 1) * 22
                const active = !done && progress > i * 22
                return (
                  <div key={stage} style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '6px 14px', borderRadius: 'var(--radius-full)',
                    background: done ? 'var(--accent-success-muted)' : active ? 'var(--accent-muted)' : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${done ? 'rgba(52,211,153,0.2)' : active ? 'rgba(96,165,250,0.2)' : 'var(--border)'}`,
                    fontSize: 11, fontWeight: 600,
                    color: done ? 'var(--accent-success)' : active ? 'var(--accent)' : 'var(--text-muted)',
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
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            <span className="material-symbols-outlined">cloud_upload</span>
            <h3>{t('dropTitle')}</h3>
            <p>{t('dropSub')}</p>

            <div style={{ display: 'flex', justifyContent: 'center', gap: 6, marginTop: 16, flexWrap: 'wrap' }}>
              {['PDF', 'PNG', 'JPG', 'TIFF'].map(fmt => (
                <span key={fmt} className="badge badge-blue">{fmt}</span>
              ))}
            </div>

            <div style={{
              display: 'inline-flex', alignItems: 'center', gap: 6,
              marginTop: 20, padding: '6px 14px', borderRadius: 'var(--radius-full)',
              background: 'var(--accent-success-muted)',
              border: '1px solid rgba(52,211,153,0.15)',
              fontSize: 11, color: 'var(--accent-success)', fontWeight: 600,
            }}>
              <span className="material-symbols-outlined" style={{ fontSize: 14 }}>lock</span>
              {t('dropSecurity')}
            </div>
          </div>
        )}
      </div>
    </>
  )
}
