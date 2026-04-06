import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Camera, Layers, Brain, Database, ArrowRight, CheckCircle2 } from 'lucide-react';

export default function ProcessingPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [currentStep, setCurrentStep] = useState(0);
  const [logs, setLogs] = useState([
    { time: new Date().toLocaleTimeString(), text: 'Nhận file: QĐ_2025.pdf', type: 'info' }
  ]);

  const steps = [
    { label: 'Preprocessing\n(Stamp Removal)', icon: Layers },
    { label: 'OCR Engine\n(VietOCR)', icon: Camera },
    { label: 'LLM Reasoning\n(Llama / Qwen)', icon: Brain },
    { label: 'Structuring\n& Validation', icon: Database }
  ];

  useEffect(() => {
    // Simulate pipeline processing
    const timers = [];
    
    timers.push(setTimeout(() => {
      setCurrentStep(1);
      addLog('Đã khử nhiễu nền và xóa con dấu đỏ thành công', 'info');
      addLog('Bắt đầu nhận diện văn bản (OCR)...', 'info');
    }, 2000));
    
    timers.push(setTimeout(() => {
      setCurrentStep(2);
      addLog('Hoàn tất OCR (độ tin cậy trung bình: 96.5%)', 'success');
      addLog('Đang chuyển text cho LLM xử lý ngữ nghĩa...', 'info');
    }, 4500));
    
    timers.push(setTimeout(() => {
      setCurrentStep(3);
      addLog('LLM phân tích hoàn tất. Loại VB: Quyết định', 'success');
      addLog('Đang chuẩn hóa schema JSON...', 'info');
    }, 7500));
    
    timers.push(setTimeout(() => {
      setCurrentStep(4);
      addLog('Hoàn tất toàn bộ chu trình xử lý.', 'success');
      setTimeout(() => navigate(`/results/${id}`), 1000);
    }, 9000));

    return () => timers.forEach(clearTimeout);
  }, [id, navigate]);

  const addLog = (text, type) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), text, type }]);
  };

  return (
    <div className="processing-page">
      <header className="page-header" style={{padding:0, marginBottom: '24px'}}>
        <h2 className="page-title">Đang xử lý Document #{id}</h2>
        <p className="page-subtitle">Hệ thống đang bóc tách tự động</p>
      </header>

      <div className="card" style={{marginBottom: '24px'}}>
        <div className="pipeline-container">
          {steps.map((step, idx) => {
            const Icon = step.icon;
            let status = 'pending';
            if (idx < currentStep) status = 'done';
            if (idx === currentStep) status = 'active';

            return (
              <div key={idx} style={{display:'flex', alignItems:'center', flex:1}}>
                <div className={`pipeline-step ${status}`}>
                  <div className="pipeline-icon-wrap">
                    {status === 'done' ? <CheckCircle2 size={24} color="var(--accent-success)" /> : <Icon size={24} color="currentColor" />}
                  </div>
                  <div className="pipeline-label" style={{whiteSpace: 'pre-line'}}>{step.label}</div>
                </div>
                {idx < steps.length - 1 && (
                  <ArrowRight className="pipeline-arrow" />
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="card" style={{padding:0, overflow:'hidden'}}>
        <div style={{padding:'12px 20px', borderBottom:'1px solid var(--border)', background: 'var(--bg-secondary)', fontSize:'12px', fontWeight:600}}>
          System Logs
        </div>
        <div className="processing-log">
          {logs.map((log, i) => (
            <div key={i} className="log-line">
              <span className="log-time">[{log.time}]</span>
              <span className={`log-${log.type === 'success' ? 'info' : log.type}`}>{log.text}</span>
            </div>
          ))}
          {currentStep < 4 && (
            <div className="log-line" style={{marginTop:'8px', opacity:0.7}}>
              <span className="log-time">[{new Date().toLocaleTimeString()}]</span>
              <span className="log-info" style={{display:'flex', alignItems:'center', gap:'8px'}}>
                 Đang xử lý bước {currentStep + 1}... <span className="spin" style={{display:'inline-block', width:'12px', height:'12px', border:'2px solid var(--accent)', borderTopColor:'transparent', borderRadius:'50%'}}></span>
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
