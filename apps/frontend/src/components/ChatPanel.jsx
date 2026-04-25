import { useState } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000'

export default function ChatPanel({ documentId, context }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!input.trim()) return

    const userMsg = { role: 'user', text: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await axios.post(`${API_BASE}/api/chat`, {
        question: input,
        document_id: documentId,
        context: context,
      })
      setMessages(prev => [...prev, { role: 'assistant', text: res.data.answer }])
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: 'Lỗi: Không thể kết nối với AI. Kiểm tra Ollama đang chạy.'
      }])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="chat-panel">
      <div className="pane-header">
        <span className="pane-header-label">
          <span className="material-symbols-outlined" style={{fontSize: 16, color: '#00d2ff'}}>smart_toy</span>
          DOCUMENT Q&A
        </span>
        <span className="pane-header-badge">Qwen2.5-7B</span>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{textAlign: 'center', padding: 40, color: 'var(--outline)'}}>
            <span className="material-symbols-outlined" style={{fontSize: 40, opacity: 0.4}}>forum</span>
            <p style={{marginTop: 8}}>Hỏi bất kỳ câu hỏi nào về tài liệu...</p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            {msg.text}
          </div>
        ))}
        {loading && (
          <div className="chat-message assistant" style={{opacity: 0.6}}>
            <span className="material-symbols-outlined animate-spin" style={{fontSize: 16}}>autorenew</span>
            {' '}Đang phân tích...
          </div>
        )}
      </div>

      <div className="chat-input-area">
        <input
          type="text"
          placeholder="Hỏi về văn bản... (VD: Ai là người ký?)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button onClick={sendMessage} disabled={loading}>
          <span className="material-symbols-outlined">send</span>
        </button>
      </div>
    </div>
  )
}
