import { useState, useEffect } from 'react'
import { useLocale } from '../LocaleContext'

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

export default function ExtractionPanel({ data = {}, onUpdate, processing = false, onFocusField }) {
  const [showJson, setShowJson] = useState(true)
  const [editData, setEditData] = useState(data)
  const { t } = useLocale()

  useEffect(() => {
    setEditData(data)
  }, [data])

  const FIELDS = [
    { key: 'so_hieu', label: t('docId'), type: 'input' },
    { key: 'ngay_ban_hanh', label: t('issueDate'), type: 'input' },
    { key: 'loai_van_ban', label: t('docType'), type: 'input' },
    { key: 'co_quan_ban_hanh', label: t('issuingAuth'), type: 'input' },
    { key: 'nguoi_ky', label: t('signer'), type: 'input' },
    { key: 'trich_yeu', label: t('abstract'), type: 'textarea' },
  ]

  const handleChange = (key, value) => {
    const updated = { ...editData, [key]: value }
    setEditData(updated)
    if (onUpdate) onUpdate(updated)
  }

  const confidence = data._confidence || {}

  const handleFocus = (key, value) => {
    if (!value || !data.ocr_lines || !onFocusField) {
      if (onFocusField) onFocusField(null)
      return
    }
    
    const valStr = String(value).toLowerCase().trim()
    if (!valStr) {
      onFocusField(null)
      return
    }

    const matches = []
    const words = valStr.split(/\s+/).filter(w => w.length > 2)
    
    for (const line of data.ocr_lines) {
      if (!line.text) continue
      const lineStr = String(line.text).toLowerCase()
      
      // Exact or partial substring match
      if (valStr.includes(lineStr) || lineStr.includes(valStr)) {
        matches.push(line)
        continue
      }
      
      // Word overlap match (for multi-line abstracts)
      let wordMatches = 0
      for (const w of words) {
        if (lineStr.includes(w)) wordMatches++
      }
      if (words.length > 0 && wordMatches / words.length >= 0.5) {
        matches.push(line)
      }
    }
    
    if (matches.length > 0) {
      onFocusField(matches)
    } else {
      onFocusField(null)
    }
  }

  // Simple JSON syntax highlight
  const highlightJson = (str) => {
    return str
      .replace(/"([^"]+)":/g, '<span style="color:#60a5fa">"$1"</span>:')
      .replace(/: "([^"]*)"/g, ': <span style="color:#34d399">"$1"</span>')
      .replace(/: (\d+)/g, ': <span style="color:#fbbf24">$1</span>')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden', minHeight: 0 }}>
      <div className="pane-header">
        <span className="pane-header-label">
          <span className="material-symbols-outlined" style={{fontSize: 16, color: 'var(--accent-cyan)'}}>code_blocks</span>
          {t('structured')}
        </span>
        <span className="pane-header-badge">{processing ? t('extracting') : 'JSON • 100%'}</span>
      </div>
      <div className="pane-body">
        <div className="extraction-panel">
          {processing ? (
            <div style={{textAlign: 'center', padding: 60, color: 'var(--text-muted)'}}>
              <span className="material-symbols-outlined spin" style={{fontSize: 40, color: 'var(--accent)'}}>autorenew</span>
              <p style={{marginTop: 16}}>{t('extracting')}</p>
            </div>
          ) : (
            <>
              <div style={{
                background: 'var(--bg-elevated)', border: '1px solid var(--border)',
                borderRadius: 'var(--radius)', padding: 16, marginBottom: 20,
                fontSize: 12
              }}>
                <h4 style={{ margin: '0 0 12px 0', fontSize: 13, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent)' }}>psychology</span>
                  Tiến trình AI
                </h4>
                <ul style={{ margin: 0, paddingLeft: 20, color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <li>Tiền xử lý & Khử nhiễu ảnh (Deskew & Denoise)</li>
                  <li>
                    <strong>Phát hiện dấu (YOLOv8 & HybridMatting):</strong> Tách thành công <strong style={{color: 'var(--accent-error)'}}>{data.total_stamps || 0}</strong> con dấu.
                  </li>
                  <li>Nhận dạng ký tự (VietOCR)</li>
                  <li>Trích xuất thông tin (Qwen2.5-7B)</li>
                </ul>
                {data.processing_time && (
                  <div style={{ marginTop: 12, paddingTop: 12, borderTop: '1px dashed var(--border)', color: 'var(--text-muted)' }}>
                    <span className="material-symbols-outlined" style={{ fontSize: 14, verticalAlign: 'middle', marginRight: 4 }}>timer</span>
                    Tổng thời gian: {data.processing_time} giây
                  </div>
                )}
              </div>

              <div className="stagger">
                {FIELDS.map(field => (
                  <div className="extraction-field fade-in-up" key={field.key}>
                    <label>
                      {field.label}
                      <ConfidenceBadge value={confidence[field.key] || 0.95} />
                    </label>
                    {field.type === 'textarea' ? (
                      <textarea
                        value={editData[field.key] || ''}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        onFocus={() => handleFocus(field.key, editData[field.key])}
                        rows={3}
                      />
                    ) : (
                      <input
                        type="text"
                        value={editData[field.key] || ''}
                        onChange={(e) => handleChange(field.key, e.target.value)}
                        onFocus={() => handleFocus(field.key, editData[field.key])}
                      />
                    )}
                  </div>
                ))}
              </div>

              <button className="json-toggle-btn" onClick={() => setShowJson(!showJson)}>
                <span className="material-symbols-outlined" style={{fontSize: 18}}>data_object</span>
                {showJson ? t('hideJson') : t('viewJson')}
              </button>

              {showJson && (
                <pre
                  style={{
                    background: 'var(--bg-primary)', color: 'var(--text-secondary)',
                    padding: 16, borderRadius: 'var(--radius-sm)', fontSize: 12,
                    fontFamily: 'var(--font-mono)', overflow: 'auto',
                    maxHeight: 300, marginTop: 8,
                    border: '1px solid var(--border)',
                  }}
                  dangerouslySetInnerHTML={{
                    __html: highlightJson(JSON.stringify(editData, null, 2))
                  }}
                />
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
