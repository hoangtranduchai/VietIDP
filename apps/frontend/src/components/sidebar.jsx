import { NavLink } from 'react-router-dom';
import { Upload, FileSearch, Clock, Settings, HelpCircle } from 'lucide-react';

export default function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <h1>VietIDP</h1>
        <p>Hành chính thông minh</p>
      </div>
      
      <div className="sidebar-section-label">Chức năng chính</div>
      <nav className="sidebar-nav">
        <NavLink to="/" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
          <Upload size={18} className="nav-icon" />
          <span>Tải lên văn bản</span>
        </NavLink>

        <NavLink to="/history" className={({isActive}) => `nav-item ${isActive ? 'active' : ''}`}>
          <Clock size={18} className="nav-icon" />
          <span>Lịch sử xử lý</span>
        </NavLink>
      </nav>



      <div className="sidebar-footer">
        <p className="sidebar-footer-text">
          Đề tài NCKH <strong>SV 2026</strong>
          <br/>LLM + OCR Engine
        </p>
      </div>
    </aside>
  );
}
