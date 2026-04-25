import { createContext, useContext, useState, useEffect } from 'react'

const LocaleContext = createContext()

const translations = {
  vi: {
    // Sidebar
    brandTitle: 'IDP Console',
    brandSub: 'Bảo mật Nội bộ',
    uploadBtn: 'Tải lên Văn bản',
    navIngestion: 'Nạp Văn Bản',
    navOCR: 'Trích Xuất OCR',
    navChat: 'Hỏi Đáp AI',
    navHistory: 'Lịch Sử',
    navExport: 'Xuất Dữ Liệu',
    navSystem: 'Hệ Thống',
    // TopBar
    appTitle: 'VietIDP Enterprise',
    localNode: 'Máy cục bộ: Hoạt động',
    // Upload
    dropTitle: 'Kéo thả văn bản vào đây',
    dropSub: 'Hỗ trợ PDF, PNG, JPG, TIFF • Tối đa 20MB',
    dropSecurity: '100% xử lý ngoại tuyến — dữ liệu không rời máy bạn',
    processing: 'Đang xử lý văn bản...',
    pipelineRun: 'Đang chạy YOLO → OCR → LLM',
    // Workspace
    selectDoc: 'Chọn tài liệu',
    exportExcel: 'Xuất Excel',
    saveToDB: 'Lưu CSDL',
    runValidation: 'Chạy xác thực',
    sourceDoc: 'VĂN BẢN GỐC',
    structured: 'TRÍCH XUẤT CẤU TRÚC',
    noDoc: 'Chưa có tài liệu',
    noDocSub: 'Tải lên PDF hoặc ảnh để bắt đầu',
    // Extraction
    docId: 'Số hiệu',
    issueDate: 'Ngày ban hành',
    docType: 'Loại văn bản',
    issuingAuth: 'Cơ quan ban hành',
    signer: 'Người ký',
    abstract: 'Trích yếu',
    viewJson: 'Xem JSON gốc',
    hideJson: 'Ẩn JSON gốc',
    extracting: 'Đang trích xuất thông tin...',
    // Chat
    chatTitle: 'Hỏi đáp văn bản',
    chatSub: 'Hỏi đáp trên tài liệu đã xử lý bằng Qwen2.5-7B',
    chatEmpty: 'Hỏi bất kỳ câu hỏi nào về tài liệu...',
    chatPlaceholder: 'Hỏi về văn bản... (VD: Ai là người ký?)',
    analyzing: 'Đang phân tích...',
    // History
    historyTitle: 'Lịch sử xử lý',
    loading: 'Đang tải...',
    noHistory: 'Chưa có tài liệu nào được xử lý',
    colId: 'ID', colFile: 'Tên tệp', colType: 'Loại', colSize: 'Kích thước',
    colPages: 'Trang', colStatus: 'Trạng thái', colDate: 'Ngày tải', colActions: 'Thao tác',
    // Dashboard
    dashTitle: 'Bảng điều khiển',
    totalDocs: 'Tổng văn bản',
    completed: 'Hoàn thành',
    failed: 'Lỗi',
    avgTime: 'TB thời gian',
    weeklyAct: 'Hoạt động tuần',
    docTypes: 'Loại văn bản',
    sysComponents: 'Thành phần hệ thống',
    allTime: 'Tổng cộng',
    successRate: 'tỷ lệ thành công',
    needAttention: 'Cần xử lý',
    perDoc: 'Mỗi văn bản',
    noData: 'Chưa có dữ liệu',
    // Pipeline stages
    stInput: 'Nạp', stOCR: 'OCR', stLLM: 'LLM', stValidation: 'Xác thực', stStorage: 'Lưu trữ',
  },
  en: {
    brandTitle: 'IDP Console',
    brandSub: 'Secure Local Node',
    uploadBtn: 'Upload Document',
    navIngestion: 'Ingestion',
    navOCR: 'OCR Extraction',
    navChat: 'Neural Q&A',
    navHistory: 'History',
    navExport: 'Export',
    navSystem: 'System Health',
    appTitle: 'VietIDP Enterprise',
    localNode: 'Local Node: Active',
    dropTitle: 'Drop your document here',
    dropSub: 'Supports PDF, PNG, JPG, TIFF • Max 20MB',
    dropSecurity: '100% offline processing — data never leaves your machine',
    processing: 'Processing Document...',
    pipelineRun: 'Running YOLO → OCR → LLM pipeline',
    selectDoc: 'Select a document',
    exportExcel: 'Export Excel',
    saveToDB: 'Save to DB',
    runValidation: 'Run Validation',
    sourceDoc: 'SOURCE DOCUMENT',
    structured: 'STRUCTURED EXTRACTION',
    noDoc: 'No document loaded',
    noDocSub: 'Upload a PDF or image to begin processing',
    docId: 'Document ID',
    issueDate: 'Issue Date',
    docType: 'Document Type',
    issuingAuth: 'Issuing Authority',
    signer: 'Signer',
    abstract: 'Content Abstract',
    viewJson: 'View Raw JSON',
    hideJson: 'Hide Raw JSON',
    extracting: 'Extracting information...',
    chatTitle: 'Document Q&A',
    chatSub: 'Ask questions about processed documents using Qwen2.5-7B',
    chatEmpty: 'Ask any question about the document...',
    chatPlaceholder: 'Ask about the document... (e.g., Who signed?)',
    analyzing: 'Analyzing...',
    historyTitle: 'Document History',
    loading: 'Loading...',
    noHistory: 'No documents processed yet',
    colId: 'ID', colFile: 'Filename', colType: 'Type', colSize: 'Size',
    colPages: 'Pages', colStatus: 'Status', colDate: 'Uploaded', colActions: 'Actions',
    dashTitle: 'System Dashboard',
    totalDocs: 'Total Documents',
    completed: 'Completed',
    failed: 'Failed',
    avgTime: 'Avg Processing',
    weeklyAct: 'Weekly Activity',
    docTypes: 'Document Types',
    sysComponents: 'System Components',
    allTime: 'All time',
    successRate: 'success rate',
    needAttention: 'Need attention',
    perDoc: 'Per document',
    noData: 'No data yet',
    stInput: 'Input', stOCR: 'OCR', stLLM: 'LLM', stValidation: 'Validation', stStorage: 'Storage',
  }
}

export function LocaleProvider({ children }) {
  const [locale, setLocale] = useState(() => localStorage.getItem('vietidp_locale') || 'vi')

  useEffect(() => {
    localStorage.setItem('vietidp_locale', locale)
  }, [locale])

  const t = (key) => translations[locale]?.[key] || translations.en[key] || key
  const toggleLocale = () => setLocale(prev => prev === 'vi' ? 'en' : 'vi')

  return (
    <LocaleContext.Provider value={{ locale, setLocale, toggleLocale, t }}>
      {children}
    </LocaleContext.Provider>
  )
}

export function useLocale() {
  const ctx = useContext(LocaleContext)
  if (!ctx) throw new Error('useLocale must be used within LocaleProvider')
  return ctx
}
