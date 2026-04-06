import { FileText, Download, Trash2, Eye } from 'lucide-react';

export default function HistoryPage() {
  const historyData = [
    { id: '1234', name: 'Quyet_dinh_01_2025.pdf', date: '25/05/2025', type: 'Quyết định', status: 'Hoàn thành' },
    { id: '1235', name: 'To_trinh_mua_sam.pdf', date: '24/05/2025', type: 'Tờ trình', status: 'Hoàn thành' },
    { id: '1236', name: 'Cong_van_chi_dao_22.png', date: '24/05/2025', type: 'Công văn', status: 'Lỗi' },
    { id: '1237', name: 'Hop_dong_lao_dong.pdf', date: '23/05/2025', type: 'Hợp đồng', status: 'Hoàn thành' },
    { id: '1238', name: 'Thong_bao_nghi_le.jpg', date: '20/05/2025', type: 'Thông báo', status: 'Hoàn thành' },
  ];

  return (
    <div className="history-page">
      <header className="page-header" style={{padding:0, marginBottom:'24px'}}>
        <h2 className="page-title">Lịch sử xử lý</h2>
        <p className="page-subtitle">Quản lý và tra cứu các văn bản hành chính đã được bóc tách</p>
      </header>

      {/* Stats Row */}
      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-value">1,248</div>
          <div className="stat-label">Tổng văn bản</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">98.5%</div>
          <div className="stat-label">Độ chính xác trung bình</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">3.2s</div>
          <div className="stat-label">Thời gian XL 1 trang</div>
        </div>
        <div className="stat-card">
          <div className="stat-value" style={{background:'linear-gradient(135deg, var(--accent-success), #10b981)', WebkitBackgroundClip:'text'}}>1,230</div>
          <div className="stat-label">Hoàn thành</div>
        </div>
      </div>

      <div className="card" style={{padding:0}}>
        <table className="history-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Tên File</th>
              <th>Loại VB</th>
              <th>Ngày Xử Lý</th>
              <th>Trạng thái</th>
              <th style={{textAlign:'right'}}>Thao tác</th>
            </tr>
          </thead>
          <tbody>
            {historyData.map(row => (
              <tr key={row.id}>
                <td style={{fontWeight:600}} color="var(--text-muted)">#{row.id}</td>
                <td>
                  <div style={{display:'flex', alignItems:'center', gap:'8px'}}>
                    <FileText size={16} color="var(--accent)" />
                    {row.name}
                  </div>
                </td>
                <td>{row.type}</td>
                <td>{row.date}</td>
                <td>
                  <span className={`badge ${row.status === 'Hoàn thành' ? 'badge-green' : 'badge-red'}`}>
                    {row.status}
                  </span>
                </td>
                <td style={{textAlign:'right'}}>
                  <div style={{display:'flex', gap:'8px', justifyContent:'flex-end'}}>
                    <button className="btn btn-ghost" style={{padding:'6px'}}><Eye size={16}/></button>
                    <button className="btn btn-ghost" style={{padding:'6px'}}><Download size={16}/></button>
                    <button className="btn btn-ghost" style={{padding:'6px', color:'var(--accent-error)'}}><Trash2 size={16}/></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
