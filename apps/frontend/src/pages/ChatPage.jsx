import { useState } from 'react'
import ChatPanel from '../components/ChatPanel'

export default function ChatPage() {
  const [docId, setDocId] = useState('')

  return (
    <>
      <header className="topbar">
        <h1 className="topbar-title">NeuralIDP Enterprise</h1>
        <div className="topbar-status">
          <span className="topbar-status-dot" />
          Local Node: Active
        </div>
      </header>

      <div className="workspace-bar">
        <div>
          <h2>Document Q&A</h2>
          <p>Hỏi đáp trên tài liệu đã xử lý bằng Qwen2.5-7B</p>
        </div>
        <div className="workspace-actions">
          <input
            type="number"
            placeholder="Document ID"
            value={docId}
            onChange={(e) => setDocId(e.target.value)}
            style={{
              padding: '8px 12px', border: '1px solid var(--border-subtle)',
              borderRadius: 6, width: 140, fontSize: 14,
            }}
          />
        </div>
      </div>

      <div style={{flex: 1, display: 'flex', padding: 24}}>
        <div className="pane" style={{flex: 1}}>
          <ChatPanel documentId={docId ? parseInt(docId) : null} />
        </div>
      </div>
    </>
  )
}
