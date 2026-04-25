import { useState } from 'react'
import { useLocale } from '../LocaleContext'
import { chatWithDocument } from '../services/api'

export default function ChatPanel({ documentId, context }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const { t } = useLocale()

  const sendMessage = async () => {
    if (!input.trim()) return
    const userMsg = { role: 'user', text: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await chatWithDocument(input, documentId, context)
      setMessages(prev => [...prev, { role: 'assistant', text: res.answer }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Error: Cannot connect to AI. Check if Ollama is running.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  return (
    <div className="chat-panel">
      <div className="pane-header">
        <span className="pane-header-label">
          <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent-cyan)' }}>smart_toy</span>
          DOCUMENT Q&A
        </span>
        <span className="pane-header-badge">Qwen2.5-7B</span>
      </div>
      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: 40, color: 'var(--text-muted)' }}>
            <span className="material-symbols-outlined float" style={{ fontSize: 44, opacity: 0.3, color: 'var(--accent)' }}>forum</span>
            <p style={{ marginTop: 12, fontSize: 13 }}>{t('chatEmpty')}</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>{msg.text}</div>
        ))}
        {loading && (
          <div className="chat-message assistant" style={{ opacity: 0.7 }}>
            <div className="typing-dots"><span /><span /><span /></div>
          </div>
        )}
      </div>
      <div className="chat-input-area">
        <input
          type="text" placeholder={t('chatPlaceholder')}
          value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown} disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          <span className="material-symbols-outlined">send</span>
        </button>
      </div>
    </div>
  )
}
