import { useState } from 'react'
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

export default function ExtractionPanel({ data = {}, onUpdate, processing = false }) {
  const [showJson, setShowJson] = useState(false)
  const [editData, setEditData] = useState(data)
  const { t } = useLocale()

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

  // Simple JSON syntax highlight
  const highlightJson = (str) => {
    return str
      .replace(/"([^"]+)":/g, '<span style="color:#60a5fa">"$1"</span>:')
      .replace(/: "([^"]*)"/g, ': <span style="color:#34d399">"$1"</span>')
      .replace(/: (\d+)/g, ': <span style="color:#fbbf24">$1</span>')
  }

  return (
    <div className="pane pane-extraction">
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
