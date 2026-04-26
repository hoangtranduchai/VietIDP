import { useEffect, useState } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import TopBar from '../layouts/TopBar'
import { getTaskStatus } from '../services/api'

export default function ProcessingPage() {
  const { id } = useParams() // task_id
  const [searchParams] = useSearchParams()
  const docId = searchParams.get('docId')
  const navigate = useNavigate()
  const { t } = useLocale()
  const [currentStep, setCurrentStep] = useState(0)
  const [logs, setLogs] = useState([
    { time: new Date().toLocaleTimeString(), text: `${t('procReceived')} Task #${id.slice(0,8)}...`, type: 'info' }
  ])

  const STEPS = [
    { key: 'preprocess', label: t('procStepStamp'), icon: 'layers' },
    { key: 'ocr', label: t('procStepOCR'), icon: 'document_scanner' },
    { key: 'llm', label: t('procStepLLM'), icon: 'psychology' },
    { key: 'validate', label: t('procStepValidate'), icon: 'database' },
  ]

  const addLog = (text, type = 'info') => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), text, type }])
  }

  useEffect(() => {
    if (!id) return;
    
    const interval = setInterval(async () => {
      try {
        const res = await getTaskStatus(id);
        
        if (res.progress?.message) {
            setLogs(prev => {
               const lastLog = prev[prev.length - 1];
               if (lastLog.text !== res.progress.message) {
                   return [...prev, { time: new Date().toLocaleTimeString(), text: res.progress.message, type: 'info' }];
               }
               return prev;
            });
        }

        if (res.status === 'SUCCESS') {
            clearInterval(interval);
            setCurrentStep(4);
            addLog(t('procComplete'), 'success');
            setTimeout(() => {
               // Fallback to res.result.document_id if docId is missing
               const finalDocId = docId || res.result?.document_id || id;
               navigate(`/workspace/${finalDocId}`);
            }, 1500);
        } else if (res.status === 'FAILURE') {
            clearInterval(interval);
            addLog(`Error: ${res.error || 'Failed to process'}`, 'error');
        } else if (res.status === 'PROGRESS') {
            const pct = res.progress?.progress || 0;
            if (pct < 20) setCurrentStep(0);
            else if (pct < 80) setCurrentStep(1);
            else if (pct < 95) setCurrentStep(2);
            else setCurrentStep(3);
        }
      } catch (err) {
        console.error('Polling error', err);
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [id, docId, navigate, t]);

  const pipeline = STEPS.map((s, i) => ({
    ...s,
    completed: i < currentStep,
    active: i === currentStep,
  }))

  return (
    <>
      <TopBar pipeline={pipeline} />

      <div className="page-container" style={{ maxWidth: 800, margin: '0 auto' }}>
        <h1 style={{ marginBottom: 8 }}>{t('procTitle')} #{id}</h1>
        <p style={{ color: 'var(--text-muted)', marginBottom: 28, fontSize: 13 }}>
          {t('procSub')}
        </p>

        {/* Pipeline visual */}
        <div className="card" style={{ marginBottom: 24, padding: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            {STEPS.map((step, i) => {
              const done = i < currentStep
              const active = i === currentStep
              return (
                <div key={step.key} style={{ display: 'flex', alignItems: 'center', flex: 1 }}>
                  <div style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
                    flex: '0 0 auto', minWidth: 80,
                  }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: 12,
                      background: done ? 'var(--accent-success-muted)' : active ? 'var(--accent-muted)' : 'var(--bg-hover)',
                      border: `1px solid ${done ? 'rgba(52,211,153,0.3)' : active ? 'rgba(96,165,250,0.3)' : 'var(--border)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.5s var(--ease)',
                      boxShadow: active ? '0 0 20px rgba(96,165,250,0.2)' : done ? '0 0 15px rgba(52,211,153,0.15)' : 'none',
                    }}>
                      <span className={`material-symbols-outlined ${active ? 'spin' : ''}`} style={{
                        fontSize: 22,
                        color: done ? 'var(--accent-success)' : active ? 'var(--accent)' : 'var(--text-muted)',
                      }}>{done ? 'check_circle' : active ? 'autorenew' : step.icon}</span>
                    </div>
                    <span style={{
                      fontSize: 11, fontWeight: 600, textAlign: 'center',
                      color: done ? 'var(--accent-success)' : active ? 'var(--accent)' : 'var(--text-muted)',
                    }}>{step.label}</span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div style={{
                      flex: 1, height: 2, margin: '0 8px',
                      background: done ? 'var(--accent-success)' : 'var(--border)',
                      borderRadius: 1, transition: 'background 0.5s',
                      marginBottom: 24,
                    }} />
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* Logs */}
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{
            padding: '10px 16px', borderBottom: '1px solid var(--border)',
            fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.06em', color: 'var(--text-muted)',
          }}>{t('procLogs')}</div>
          <div style={{ padding: 16, fontFamily: 'var(--font-mono)', fontSize: 12, maxHeight: 300, overflowY: 'auto' }}>
            {logs.map((log, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 6, animation: 'fadeIn 0.3s ease' }}>
                <span style={{ color: 'var(--text-muted)', flexShrink: 0 }}>[{log.time}]</span>
                <span style={{
                  color: log.type === 'success' ? 'var(--accent-success)' : log.type === 'error' ? 'var(--accent-error)' : 'var(--text-secondary)',
                }}>{log.text}</span>
              </div>
            ))}
            {currentStep < 4 && (
              <div style={{ display: 'flex', gap: 10, opacity: 0.6, alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)' }}>[{new Date().toLocaleTimeString()}]</span>
                <span style={{ color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 6 }}>
                  {t('procStep')} {currentStep + 1}...
                  <span className="spin" style={{
                    display: 'inline-block', width: 10, height: 10,
                    border: '2px solid var(--accent)', borderTopColor: 'transparent', borderRadius: '50%',
                  }} />
                </span>
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
