import { useState, useRef, useEffect } from 'react'
import { useLocale } from '../LocaleContext'
import { chatWithDocument } from '../services/api'
import ReactMarkdown from 'react-markdown'
import { toast } from 'react-toastify'
import { MOCK_CHAT_RESPONSES, MOCK_SUGGESTED_QUESTIONS } from '../data/mockData'

export default function ChatPanel({ documentId, context }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const { t, locale } = useLocale()
  const mockResponseIdx = useRef(0)
  const messagesEndRef = useRef(null)
  const autoSummarizedDocId = useRef(null)

  const QUICK_ACTIONS = [
    { label: 'Tóm tắt nội dung', prompt: 'Hãy tóm tắt ngắn gọn nội dung của tài liệu này.' },
    { label: 'Liệt kê thực thể', prompt: 'Hãy liệt kê tất cả cá nhân, tổ chức, cơ quan liên quan trong tài liệu.' },
    { label: 'Điểm lưu ý', prompt: 'Dựa vào nội dung tài liệu, hãy chỉ ra các điểm cần lưu ý hoặc rủi ro pháp lý tiềm ẩn.' }
  ]

  // Auto-Summary Feature
  useEffect(() => {
    if (documentId && context && context.trim() && autoSummarizedDocId.current !== documentId && messages.length === 0) {
      autoSummarizedDocId.current = documentId
      
      const generateSummary = async () => {
        setLoading(true)
        setMessages([{ role: 'assistant', text: '👋 Chào bạn, tôi đang đọc và tóm tắt tài liệu này...' }])
        
        try {
          const prompt = "Hãy đóng vai một trợ lý AI thông minh. Viết một đoạn tóm tắt siêu ngắn gọn nhưng đầy đủ ý chính (loại văn bản, nội dung trọng tâm) của tài liệu này. Xuống dòng và hỏi người dùng xem họ có cần bạn trích xuất hay tìm kiếm thông tin gì cụ thể không."
          const res = await chatWithDocument(prompt, documentId, context)
          setMessages([{ role: 'assistant', text: res.answer }])
        } catch {
          // Fallback: mock auto-summary
          const mockResp = MOCK_CHAT_RESPONSES[locale] || MOCK_CHAT_RESPONSES.vi
          setMessages([{ role: 'assistant', text: `👋 ${locale === 'vi' ? 'Chào bạn!' : 'Hello!'} ${locale === 'vi' ? 'Đây là bản tóm tắt tài liệu:' : 'Here is the document summary:'}

${mockResp[2]?.a || 'Document loaded successfully.'}` }])
        } finally {
          setLoading(false)
        }
      }
      generateSummary()
    }
  }, [documentId, context, messages.length])

  const sendMessage = async (overrideInput = null) => {
    const textToSend = typeof overrideInput === 'string' ? overrideInput : input
    if (!textToSend.trim()) return
    if (!context && !documentId) return
    const userMsg = { role: 'user', text: textToSend }
    setMessages(prev => [...prev, userMsg])
    if (!overrideInput) setInput('')
    setLoading(true)

    try {
      const res = await chatWithDocument(textToSend, documentId, context)
      setMessages(prev => [...prev, { role: 'assistant', text: res.answer }])
    } catch {
      // Fallback: mock response
      const mockResp = MOCK_CHAT_RESPONSES[locale] || MOCK_CHAT_RESPONSES.vi
      const idx = mockResponseIdx.current % mockResp.length
      mockResponseIdx.current++
      setMessages(prev => [...prev, {
        role: 'assistant',
        text: mockResp[idx]?.a || `${locale === 'vi' ? 'Xin lỗi, tôi không thể trả lời câu hỏi này.' : 'Sorry, I cannot answer this question.'}`
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
            {/* Suggested questions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 16, alignItems: 'center' }}>
              {(MOCK_SUGGESTED_QUESTIONS[locale] || MOCK_SUGGESTED_QUESTIONS.vi).slice(0, 3).map((q, i) => (
                <button key={i} onClick={() => sendMessage(q)}
                  style={{ padding: '8px 16px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-full)', color: 'var(--accent)', fontSize: 12, fontWeight: 500, cursor: 'pointer', transition: 'all 0.2s', maxWidth: 280, textAlign: 'center' }}
                  onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent)'}
                  onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border)'}>
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-message ${msg.role}`}>
            {msg.role === 'assistant' && (
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8, borderBottom: '1px solid var(--border)', paddingBottom: 6 }}>
                <span className="material-symbols-outlined" style={{ fontSize: 16, color: 'var(--accent-cyan)' }}>smart_toy</span>
                <button 
                  onClick={() => { navigator.clipboard.writeText(msg.text); toast.success('Đã sao chép!'); }}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', padding: 2, borderRadius: 4 }}
                  title="Sao chép"
                  className="hover-bg"
                >
                  <span className="material-symbols-outlined" style={{ fontSize: 14 }}>content_copy</span>
                </button>
              </div>
            )}
            {msg.role === 'user' ? (
              msg.text
            ) : (
              <div className="markdown-body" style={{ fontSize: 13, lineHeight: 1.6, color: 'var(--text-secondary)' }}>
                <ReactMarkdown>{msg.text}</ReactMarkdown>
              </div>
            )}
          </div>
        ))}
        {loading && (
          <div className="chat-message assistant" style={{ opacity: 0.7 }}>
            <div className="typing-dots"><span /><span /><span /></div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      
      {messages.length === 1 && !loading && (
        <div style={{ display: 'flex', gap: 8, padding: '0 16px 16px', overflowX: 'auto', flexWrap: 'wrap' }}>
          {QUICK_ACTIONS.map((action, i) => (
            <button 
              key={i} 
              onClick={() => sendMessage(action.prompt)} 
              style={{ padding: '6px 12px', background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 'var(--radius-full)', color: 'var(--accent)', fontSize: 11, fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap', transition: 'all 0.2s', boxShadow: 'var(--shadow-sm)' }}
              onMouseOver={e => e.currentTarget.style.borderColor = 'var(--accent)'}
              onMouseOut={e => e.currentTarget.style.borderColor = 'var(--border)'}
            >
              {action.label}
            </button>
          ))}
        </div>
      )}

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
