import { useState } from 'react'
import { useLocale } from '../LocaleContext'
import TopBar from '../layouts/TopBar'
import ChatPanel from '../components/ChatPanel'

export default function ChatPage() {
  const [docId, setDocId] = useState('')
  const { t } = useLocale()

  return (
    <>
      <TopBar />
      <div className="workspace-bar">
        <div>
          <h2>{t('chatTitle')}</h2>
          <p>{t('chatSub')}</p>
        </div>
        <div className="workspace-actions">
          <input
            type="number"
            placeholder="Document ID"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            style={{
              padding: '8px 12px', border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)', width: 140, fontSize: 14,
              background: 'var(--bg-primary)', color: 'var(--text-primary)',
              outline: 'none', fontFamily: 'var(--font-mono)',
            }}
          />
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', padding: 20 }}>
        <div className="pane" style={{ flex: 1 }}>
          <ChatPanel documentId={docId ? parseInt(docId) : null} />
        </div>
      </div>
    </>
  )
}
