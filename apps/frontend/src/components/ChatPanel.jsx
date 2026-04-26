import { useState, useRef, useEffect } from 'react'
import { useLocale } from '../LocaleContext'
import { chatWithDocument } from '../services/api'

export default function ChatPanel({ documentId, context, initialSummary }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const { t } = useLocale()
  const messagesEndRef = useRef(null)
  const autoSummarizedDocId = useRef(null)

  // Bug 9 fix: Auto-scroll to latest message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Auto-Summary Feature
  useEffect(() => {
    if (documentId && context && autoSummarizedDocId.current !== documentId && messages.length === 0) {
      autoSummarizedDocId.current = documentId
      
      // If we already have a summary from OCR Pipeline, show it instantly
      if (initialSummary && initialSummary.trim() !== '') {
        setMessages([{ 
          role: 'assistant', 
          text: `👋 Chào bạn, tôi đã đọc xong tài liệu. Dưới đây là tóm tắt nhanh nội dung:\n\n**${initialSummary}**\n\nBạn có muốn tôi phân tích sâu hơn hay tìm kiếm thông tin gì cụ thể trong văn bản này không?` 
        }])
      } else {
        // Fallback: Generate summary via LLM if initialSummary is missing
        const generateSummary = async () => {
          setLoading(true)
          setMessages([{ role: 'assistant', text: '👋 Chào bạn, tôi đang đọc và tóm tắt tài liệu này...' }])
          
          try {
            const prompt = "Hãy đóng vai một trợ lý AI thông minh. Viết một đoạn tóm tắt siêu ngắn gọn nhưng đầy đủ ý chính (loại văn bản, nội dung trọng tâm) của tài liệu này. Xuống dòng và hỏi người dùng xem họ có cần bạn trích xuất hay tìm kiếm thông tin gì cụ thể không."
            const res = await chatWithDocument(prompt, documentId, context)
            setMessages([{ role: 'assistant', text: res.answer }])
          } catch {
            setMessages([])
          } finally {
            setLoading(false)
          }
        }
        generateSummary()
      }
    }
  }, [documentId, context, initialSummary, messages.length])

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
        <div ref={messagesEndRef} />
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
