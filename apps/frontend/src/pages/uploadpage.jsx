import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export default function UploadPage() {
  const navigate = useNavigate()
  const [uploading, setUploading] = useState(false)
  const [progress, setProgress] = useState(0)

  const onDrop = useCallback(async (files) => {
    if (files.length === 0) return

    setUploading(true)
    setProgress(10)

    const formData = new FormData()
    formData.append('file', files[0])

    try {
      setProgress(30)
      const res = await axios.post(`${API_BASE}/api/process_document`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (e) => {
          const pct = Math.round((e.loaded / e.total) * 40) + 30
          setProgress(pct)
        }
      })

      setProgress(100)
      if (res.data.document_id) {
        navigate(`/workspace/${res.data.document_id}`)
      }
    } catch (err) {
      alert('Lỗi xử lý: ' + (err.response?.data?.detail || err.message))
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
      <header className="topbar">
        <h1 className="topbar-title">NeuralIDP Enterprise</h1>
        <div className="topbar-status">
          <span className="topbar-status-dot" />
          Local Node: Active
        </div>
      </header>

      <div className="upload-page">
        {uploading ? (
          <div style={{textAlign: 'center'}}>
            <span className="material-symbols-outlined animate-spin" style={{fontSize: 56, color: 'var(--primary-container)'}}>autorenew</span>
            <h3 style={{fontFamily: 'Epilogue', fontSize: 22, fontWeight: 600, color: 'var(--primary)', margin: '20px 0 8px'}}>
              Processing Document...
            </h3>
            <p style={{color: 'var(--outline)', marginBottom: 24}}>
              Running YOLO → OCR → LLM pipeline
            </p>
            <div style={{
              width: 400, height: 6, background: 'var(--surface-container)',
              borderRadius: 3, overflow: 'hidden', margin: '0 auto',
            }}>
              <div style={{
                height: '100%', background: 'var(--secondary-container)',
                borderRadius: 3, width: `${progress}%`,
                transition: 'width 0.3s ease',
              }} />
            </div>
            <p style={{color: 'var(--outline)', fontSize: 13, marginTop: 8}}>{progress}%</p>
          </div>
        ) : (
          <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
            <input {...getInputProps()} />
            <span className="material-symbols-outlined">cloud_upload</span>
            <h3>Drop your document here</h3>
            <p>Support PDF, PNG, JPG, TIFF • Max 20MB</p>
            <p style={{marginTop: 16, fontSize: 12, color: 'var(--outline)'}}>
              100% offline processing — data never leaves your machine
            </p>
          </div>
        )}
      </div>
    </>
  )
}
