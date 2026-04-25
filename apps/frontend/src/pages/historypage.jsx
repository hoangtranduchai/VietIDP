import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export default function HistoryPage() {
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    try {
      const res = await axios.get(`${API_BASE}/api/documents?limit=50`)
      setDocs(res.data.documents || [])
    } catch (err) {
      console.error('Failed to load documents:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Xóa tài liệu này?')) return
    try {
      await axios.delete(`${API_BASE}/api/documents/${id}`)
      setDocs(docs.filter(d => d.id !== id))
    } catch (err) {
      alert('Lỗi xóa: ' + err.message)
    }
  }

  const formatDate = (iso) => {
    if (!iso) return ''
    return new Date(iso).toLocaleString('vi-VN', {
      day: '2-digit', month: '2-digit', year: 'numeric',
      hour: '2-digit', minute: '2-digit'
    })
  }

  const formatSize = (bytes) => {
    if (!bytes) return ''
    return (bytes / 1024).toFixed(0) + ' KB'
  }

  return (
    <>
      <header className="topbar">
        <h1 className="topbar-title">NeuralIDP Enterprise</h1>
        <div className="topbar-status">
          <span className="topbar-status-dot" />
          Local Node: Active
        </div>
      </header>

      <div className="page-container">
        <h1>Document History</h1>

        {loading ? (
          <div style={{textAlign: 'center', padding: 60, color: 'var(--outline)'}}>
            <span className="material-symbols-outlined animate-spin" style={{fontSize: 40}}>autorenew</span>
            <p style={{marginTop: 16}}>Loading documents...</p>
          </div>
        ) : docs.length === 0 ? (
          <div style={{textAlign: 'center', padding: 60, color: 'var(--outline)'}}>
            <span className="material-symbols-outlined" style={{fontSize: 56, opacity: 0.3}}>folder_open</span>
            <p style={{marginTop: 16}}>No documents processed yet</p>
          </div>
        ) : (
          <table className="doc-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Filename</th>
                <th>Type</th>
                <th>Size</th>
                <th>Pages</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {docs.map(doc => (
                <tr key={doc.id}>
                  <td style={{fontFamily: 'monospace'}}>#{doc.id}</td>
                  <td>
                    <span
                      style={{color: 'var(--primary-container)', cursor: 'pointer', fontWeight: 500}}
                      onClick={() => navigate(`/workspace/${doc.id}`)}
                    >
                      {doc.filename}
                    </span>
                  </td>
                  <td><span style={{textTransform: 'uppercase', fontSize: 12}}>{doc.file_type}</span></td>
                  <td>{formatSize(doc.file_size)}</td>
                  <td>{doc.num_pages}</td>
                  <td><span className={`status-badge ${doc.status}`}>{doc.status}</span></td>
                  <td style={{fontSize: 13, color: 'var(--outline)'}}>{formatDate(doc.created_at)}</td>
                  <td>
                    <div style={{display: 'flex', gap: 4}}>
                      <button className="btn" style={{padding: '4px 8px'}}
                        onClick={() => navigate(`/workspace/${doc.id}`)}>
                        <span className="material-symbols-outlined" style={{fontSize: 16}}>open_in_new</span>
                      </button>
                      <button className="btn" style={{padding: '4px 8px', color: 'var(--error)'}}
                        onClick={() => handleDelete(doc.id)}>
                        <span className="material-symbols-outlined" style={{fontSize: 16}}>delete</span>
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  )
}
