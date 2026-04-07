import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useNavigate } from 'react-router-dom';
import { FileUp, File, CheckCircle } from 'lucide-react';

export default function UploadPage() {
  const navigate = useNavigate();
  const [isUploading, setIsUploading] = useState(false);

  const [progress, setProgress] = useState(0);

  const onDrop = useCallback(acceptedFiles => {
    if (acceptedFiles.length > 0) {
      handleUpload(acceptedFiles[0]);
    }
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': ['.png', '.jpg', '.jpeg'],
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt']
    },
    multiple: false
  });

  const [fileType, setFileType] = useState('image'); // 'image' | 'doc'

  const handleUpload = async (file) => {
    const isDoc = file.name.endsWith('.docx') || file.name.endsWith('.txt');
    setFileType(isDoc ? 'doc' : 'image');
    setIsUploading(true);
    setProgress(0);
    
    // Simulate progress while waiting for backend
    const progressInterval = setInterval(() => {
      setProgress(prev => (prev < 90 ? prev + (isDoc ? 1 : 2) : prev));
    }, isDoc ? 400 : 100);
    
    const formData = new FormData();
    formData.append('document', file);
    
    try {
      const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';
      const endpoint = isDoc ? '/api/summarize' : '/api/process';
      const response = await fetch(`${API_URL}${endpoint}`, {
        method: 'POST',
        body: formData
      });
      
      const data = await response.json();
      clearInterval(progressInterval);
      setProgress(100);
      
      if (data.success || data.summary) {
        if (isDoc) {
          localStorage.setItem('last_summary', JSON.stringify({...data, fileName: file.name}));
          setTimeout(() => navigate('/summarize'), 500);
        } else {
          localStorage.setItem('last_processed_pages', JSON.stringify(data.pages || []));
          if (data.summary) {
            localStorage.setItem('last_summary', JSON.stringify(data));
          } else {
            localStorage.removeItem('last_summary');
          }
          setTimeout(() => navigate(`/results/${Math.random().toString(36).substring(7)}`), 500);
        }
      } else {
        alert("Lỗi AI: " + (data.error || 'Unknown error'));
        setIsUploading(false);
      }
    } catch (e) {
      clearInterval(progressInterval);
      console.error(e);
      alert("Lỗi kết nối Server Backend!");
      setIsUploading(false);
    }
  };

  return (
    <div className="upload-page">
      <header className="page-header" style={{padding:0, marginBottom: '32px'}}>
        <h2 className="page-title">Tải lên văn bản hành chính</h2>
        <p className="page-subtitle">Hệ thống hỗ trợ PDF, PNG, JPG (ưu tiên bản scan độ phân giải cao)</p>
      </header>

      <div 
        {...getRootProps()} 
        className={`upload-zone ${isDragActive ? 'drag-active' : ''}`}
        style={{ pointerEvents: isUploading ? 'none' : 'auto', opacity: isUploading ? 0.9 : 1 }}
      >
        <input {...getInputProps()} />
        
        {isUploading ? (
          <div style={{width:'80%', margin:'0 auto', textAlign:'center'}}>
             <div style={{marginBottom:'16px'}}>
               <FileUp size={36} color="var(--accent-blue)" className="pulse" style={{display:'inline-block'}}/>
             </div>
             <h3 style={{fontSize:'18px', color:'var(--text-main)', marginBottom:'12px'}}>
               Hệ thống AI đang phân tích tài liệu... {progress}%
             </h3>
             <div style={{width:'100%', height:'8px', background:'var(--border)', borderRadius:'4px', overflow:'hidden'}}>
               <div style={{
                 width: `${progress}%`, 
                 height:'100%', 
                 background:'var(--accent-blue)', 
                 transition:'width 0.2s ease-out'
               }}></div>
             </div>
             <p style={{marginTop:'12px', color:'var(--text-muted)', fontSize:'14px'}}>
               {fileType === 'doc' ? 'AI Qwen2.5:7b đang phân tích nội dung, có thể mất 30-60 giây...' : 'Đang chạy YOLOv8 + Qwen2.5:7b trích xuất thông tin'}
             </p>
          </div>
        ) : (
          <>
            <div className="upload-icon">
              <FileUp size={28} color="var(--accent)" />
            </div>
            <h3 className="upload-title">
              {isDragActive ? 'Thả file vào đây...' : 'Kéo thả file hoặc Click để chọn'}
            </h3>
            <p className="upload-sub">Kích thước tối đa: 20MB</p>
            <div className="upload-formats">
              <span className="badge badge-blue">PDF</span>
              <span className="badge badge-green">PNG</span>
              <span className="badge badge-yellow">JPG</span>
              <span style={{background: '#ede9fe', color: '#7c3aed', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: '700'}}>DOCX</span>
              <span style={{background: '#f3f4f6', color: '#4b5563', padding: '4px 10px', borderRadius: '12px', fontSize: '11px', fontWeight: '700'}}>TXT</span>
            </div>
          </>
        )}
      </div>


    </div>
  );
}
