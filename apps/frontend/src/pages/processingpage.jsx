import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate, useSearchParams, useLocation } from 'react-router-dom'
import { useLocale } from '../LocaleContext'
import TopBar from '../layouts/TopBar'
import { getTaskStatus } from '../services/api'
import { MOCK_PROCESSING_STAGES } from '../data/mockData'

export default function ProcessingPage() {
  const { id } = useParams() // task_id
  const [searchParams] = useSearchParams()
  const docId = searchParams.get('docId')
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useLocale()
  const [currentStep, setCurrentStep] = useState(0)
  const [docName, setDocName] = useState(location.state?.filename || null)
  const [isMock, setIsMock] = useState(false)
  const mockStageIdx = useRef(0)
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
    if (docId) {
      import('../services/api').then(({ getDocument }) => {
        getDocument(docId).then(doc => setDocName(doc.filename)).catch(() => {
          // Backend offline — enable mock
          setDocName('qd_02_2026_QD-TTg.pdf')
          setIsMock(true)
        })
      })
    }
  }, [docId])

  // Real backend polling
  useEffect(() => {
    if (!id || isMock) return;
    
    let failed = false
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
        if (!failed) {
          failed = true
          setIsMock(true) // Switch to mock mode on first failure
          clearInterval(interval)
        }
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [id, docId, navigate, t, isMock]);

  // Mock auto-advance demo
  useEffect(() => {
    if (!isMock) return

    const interval = setInterval(() => {
      const stages = MOCK_PROCESSING_STAGES
      const idx = mockStageIdx.current
      
      if (idx >= stages.length) {
        clearInterval(interval)
        setCurrentStep(4)
        setTimeout(() => {
          navigate(`/workspace/1`) // Navigate to mock doc #1
        }, 1500)
        return
      }

      const stage = stages[idx]
      addLog(stage.message, idx === stages.length - 1 ? 'success' : 'info')
      
      // Map progress to step
      if (stage.progress < 30) setCurrentStep(0)
      else if (stage.progress < 70) setCurrentStep(1)
      else if (stage.progress < 90) setCurrentStep(2)
      else if (stage.progress < 100) setCurrentStep(3)
      else setCurrentStep(4)
      
      mockStageIdx.current = idx + 1
    }, 1200) // Advance every 1.2s for a smooth demo

    return () => clearInterval(interval)
  }, [isMock, navigate])

  const pipeline = STEPS.map((s, i) => ({
    ...s,
    completed: i < currentStep,
    active: i === currentStep,
  }))

  return (
    <>
      <TopBar pipeline={pipeline} />

      <div className="page-container" style={{ maxWidth: 800, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8, flexWrap: 'wrap', gap: 8 }}>
          <h1>
            {docName ? `${t('procTitle')}: ${docName}` : `${t('procTitle')} #${id.slice(0, 8)}...`}
          </h1>
          {isMock && (
            <span className="badge badge-yellow" style={{ fontSize: 10 }}>
              <span className="material-symbols-outlined" style={{ fontSize: 12 }}>info</span>
              Demo Mode
            </span>
          )}
        </div>
        <p style={{ color: 'var(--text-muted)', marginBottom: 28, fontSize: 13 }}>
          {t('procSub')}
        </p>

        {/* Pipeline visual */}
        <div className="card" style={{ marginBottom: 24, padding: 20, overflowX: 'auto' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', minWidth: 600 }}>
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
                      width: 48, height: 48, borderRadius: 14,
                      background: done ? 'var(--accent-success-muted)' : active ? 'var(--accent-muted)' : 'var(--bg-hover)',
                      border: `2px solid ${done ? 'rgba(52,211,153,0.4)' : active ? 'rgba(96,165,250,0.4)' : 'var(--border)'}`,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      transition: 'all 0.5s var(--ease)',
                      boxShadow: active ? '0 0 24px rgba(96,165,250,0.25)' : done ? '0 0 18px rgba(52,211,153,0.2)' : 'none',
                    }}>
                      <span className={`material-symbols-outlined ${active ? 'spin' : ''}`} style={{
                        fontSize: 22,
                        color: done ? 'var(--accent-success)' : active ? 'var(--accent)' : 'var(--text-muted)',
                        transition: 'color 0.3s',
                      }}>{done ? 'check_circle' : active ? 'autorenew' : step.icon}</span>
                    </div>
                    <span style={{
                      fontSize: 11, fontWeight: 600, textAlign: 'center',
                      color: done ? 'var(--accent-success)' : active ? 'var(--accent)' : 'var(--text-muted)',
                      transition: 'color 0.3s',
                    }}>{step.label}</span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <div style={{ flex: 1, position: 'relative', margin: '0 8px', marginBottom: 24 }}>
                      {/* Background line */}
                      <div style={{ height: 2, background: 'var(--border)', borderRadius: 1 }} />
                      {/* Animated progress fill */}
                      <div style={{
                        position: 'absolute', top: 0, left: 0, height: 2, borderRadius: 1,
                        background: done ? 'var(--accent-success)' : active ? 'linear-gradient(90deg, var(--accent), transparent)' : 'transparent',
                        width: done ? '100%' : active ? '50%' : '0%',
                        transition: 'all 0.8s var(--ease)',
                        boxShadow: (done || active) ? '0 0 6px rgba(96,165,250,0.3)' : 'none',
                      }} />
                    </div>
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
            display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          }}>
            <span>{t('procLogs')}</span>
            <span style={{ fontSize: 10, fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
              {logs.length} entries
            </span>
          </div>
          <div style={{ padding: 16, fontFamily: 'var(--font-mono)', fontSize: 12, maxHeight: 350, overflowY: 'auto' }}>
            {logs.map((log, i) => (
              <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 8, animation: 'fadeIn 0.3s ease' }}>
                <span style={{ color: 'var(--text-muted)', flexShrink: 0, fontSize: 11 }}>[{log.time}]</span>
                <span style={{
                  color: log.type === 'success' ? 'var(--accent-success)' : log.type === 'error' ? 'var(--accent-error)' : 'var(--text-secondary)',
                  fontWeight: log.type === 'success' ? 700 : 400,
                }}>{log.text}</span>
              </div>
            ))}
            {currentStep < 4 && (
              <div style={{ display: 'flex', gap: 10, opacity: 0.6, alignItems: 'center' }}>
                <span style={{ color: 'var(--text-muted)', fontSize: 11 }}>[{new Date().toLocaleTimeString()}]</span>
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
