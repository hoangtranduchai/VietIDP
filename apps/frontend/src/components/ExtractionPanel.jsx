import { useState } from 'react'

const FIELDS = [
  { key: 'so_hieu', label: 'Document ID', icon: 'tag', type: 'input' },
  { key: 'ngay_ban_hanh', label: 'Issue Date', icon: 'calendar_today', type: 'input' },
  { key: 'loai_van_ban', label: 'Document Type', icon: 'category', type: 'input' },
  { key: 'co_quan_ban_hanh', label: 'Issuing Authority', icon: 'apartment', type: 'input' },
  { key: 'nguoi_ky', label: 'Signer', icon: 'person', type: 'input' },
  { key: 'trich_yeu', label: 'Content Abstract', icon: 'edit_document', type: 'textarea' },
]

function ConfidenceBadge({ value }) {
  const pct = Math.round((value || 0) * 100)
  const level = pct >= 95 ? 'high' : pct >= 80 ? 'medium' : 'low'
  const icon = pct >= 95 ? 'check' : 'warning'
  return (
    <span className={`confidence-badge ${level}`}>
      <span className="material-symbols-outlined" style={{fontSize: 14}}>{icon}</span>
      {pct}%
    </span>
  )
}

export default function ExtractionPanel({ data = {}, onUpdate, processing = false }) {
  const [showJson, setShowJson] = useState(false)
  const [editData, setEditData] = useState(data)

  const handleChange = (key, value) => {
    const updated = { ...editData, [key]: value }
    setEditData(updated)
    if (onUpdate) onUpdate(updated)
  }

  const confidence = data._confidence || {}

  return (
    <div className="pane pane-extraction">
      <div className="pane-header">
        <span className="pane-header-label">
          <span className="material-symbols-outlined" style={{fontSize: 16, color: '#00d2ff'}}>code_blocks</span>
          STRUCTURED EXTRACTION
        </span>
        <span className="pane-header-badge">JSON • {processing ? 'Processing...' : '100% Parsed'}</span>
      </div>
      <div className="pane-body">
        <div className="extraction-panel">
          {processing ? (
            <div style={{textAlign: 'center', padding: 60, color: 'var(--outline)'}}>
              <span className="material-symbols-outlined animate-spin" style={{fontSize: 40}}>autorenew</span>
              <p style={{marginTop: 16}}>Đang trích xuất thông tin...</p>
            </div>
          ) : (
            <>
              {FIELDS.map(field => (
                <div className="extraction-field" key={field.key}>
                  <label>
                    {field.label}
                    <ConfidenceBadge value={confidence[field.key] || 0.95} />
                  </label>
                  {field.type === 'textarea' ? (
                    <textarea
                      value={editData[field.key] || ''}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                      rows={3}
                    />
                  ) : (
                    <input
                      type="text"
                      value={editData[field.key] || ''}
                      onChange={(e) => handleChange(field.key, e.target.value)}
                    />
                  )}
                </div>
              ))}

              <button className="json-toggle-btn" onClick={() => setShowJson(!showJson)}>
                <span className="material-symbols-outlined" style={{fontSize: 18}}>data_object</span>
                {showJson ? 'Hide' : 'View'} Raw JSON Output
              </button>

              {showJson && (
                <pre style={{
                  background: '#1e293b', color: '#e2e8f0',
                  padding: 16, borderRadius: 8, fontSize: 12,
                  fontFamily: 'monospace', overflow: 'auto',
                  maxHeight: 300, marginTop: 8,
                }}>
                  {JSON.stringify(editData, null, 2)}
                </pre>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
