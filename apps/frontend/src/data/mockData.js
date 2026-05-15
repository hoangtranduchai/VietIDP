/**
 * VietIDP — Centralized Mock Data
 * ================================
 * Provides realistic mock data for ALL pages when backend is offline.
 * Data structure matches the real backend API schema exactly.
 */

// ═══════════════════════════════════════════════════════════════
// Mock Documents (matches GET /api/documents response)
// ═══════════════════════════════════════════════════════════════

export const MOCK_DOCUMENTS = [
  {
    id: 1,
    filename: 'qd_02_2026_QD-TTg.pdf',
    file_type: 'pdf',
    file_size: 2457600,
    num_pages: 12,
    status: 'completed',
    created_at: '2026-05-09T08:30:00Z',
    extraction: {
      loai_van_ban: 'Quyết định',
      so_hieu: '02/2026/QĐ-TTg',
      ngay_ban_hanh: '07/01/2026',
      co_quan_ban_hanh: 'Thủ tướng Chính phủ',
      nguoi_ky: 'Nguyễn Chí Dũng',
      trich_yeu: 'Sửa đổi, bổ sung một số điều của các Quyết định để cắt giảm, đơn giản hóa thủ tục hành chính liên quan đến hoạt động sản xuất, kinh doanh thuộc phạm vi quản lý nhà nước của Bộ Khoa học và Công nghệ',
      processing_time: 374.06,
      ocr_confidence: 0.965,
      total_stamps: 2,
      stamp_coordinates: [
        { x1: 580, y1: 1200, x2: 780, y2: 1400, confidence: 0.94, page: 1 },
        { x1: 600, y1: 2800, x2: 800, y2: 3000, confidence: 0.89, page: 12 },
      ],
      tom_tat_ngan: 'Sửa đổi, bổ sung thủ tục hành chính trong sản xuất kinh doanh thuộc Bộ KH&CN.',
      tom_tat_day_du: 'Quyết định sửa đổi, bổ sung một số điều của các Quyết định liên quan đến cắt giảm và đơn giản hóa thủ tục hành chính. Phạm vi áp dụng bao gồm hoạt động sản xuất, kinh doanh thuộc quản lý nhà nước của Bộ Khoa học và Công nghệ. Các nội dung sửa đổi tập trung vào giảm thời gian xử lý, số lượng hồ sơ, và chuyển đổi sang hình thức trực tuyến.',
      diem_chinh: [
        'Giảm 30% thời gian xử lý thủ tục hành chính so với quy định hiện hành.',
        'Chuyển đổi 15 thủ tục sang nộp hồ sơ trực tuyến toàn trình trên Cổng Dịch vụ công quốc gia.',
        'Bãi bỏ yêu cầu nộp bản sao chứng thực đối với 8 loại giấy tờ, thay thế bằng khai báo trực tuyến.',
        'Áp dụng cơ chế một cửa liên thông giữa Bộ KH&CN và các bộ, ngành liên quan.',
      ],
      van_ban_lien_quan: ['Luật Khoa học và Công nghệ 2013', 'Nghị định 08/2014/NĐ-CP', 'Quyết định 38/2021/QĐ-TTg'],
      tu_khoa: ['Thủ tục hành chính', 'Cải cách', 'Trực tuyến', 'Khoa học công nghệ', 'Một cửa'],
      linh_vuc: 'Khoa học & Công nghệ',
      thoi_han_hieu_luc: '01/03/2026',
      _confidence: {
        loai_van_ban: 0.98,
        so_hieu: 0.97,
        ngay_ban_hanh: 0.92,
        co_quan_ban_hanh: 0.96,
        nguoi_ky: 0.88,
        trich_yeu: 0.85,
      },
      ocr_lines: [
        { text: 'THỦ TƯỚNG CHÍNH PHỦ', x1: 100, y1: 50, x2: 400, y2: 80, page: 1 },
        { text: 'CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM', x1: 450, y1: 50, x2: 900, y2: 80, page: 1 },
        { text: 'Độc lập - Tự do - Hạnh phúc', x1: 500, y1: 85, x2: 850, y2: 110, page: 1 },
        { text: 'Số: 02/2026/QĐ-TTg', x1: 100, y1: 150, x2: 350, y2: 175, page: 1 },
        { text: 'Hà Nội, ngày 07 tháng 01 năm 2026', x1: 500, y1: 150, x2: 850, y2: 175, page: 1 },
        { text: 'QUYẾT ĐỊNH', x1: 350, y1: 220, x2: 600, y2: 260, page: 1 },
      ],
      full_text: 'THỦ TƯỚNG CHÍNH PHỦ\nCỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\nĐộc lập - Tự do - Hạnh phúc\n\nSố: 02/2026/QĐ-TTg\n\nHà Nội, ngày 07 tháng 01 năm 2026\n\nQUYẾT ĐỊNH\nSửa đổi, bổ sung một số điều...',
      raw_json: { pages: [{ page: 1 }] },
    },
  },
  {
    id: 2,
    filename: 'qd_02_2026_QD-UBND_DakLak.pdf',
    file_type: 'pdf',
    file_size: 1843200,
    num_pages: 8,
    status: 'completed',
    created_at: '2026-05-09T09:15:00Z',
    extraction: {
      loai_van_ban: 'Quyết định',
      so_hieu: '02/2026/QĐ-UBND',
      ngay_ban_hanh: '10/01/2026',
      co_quan_ban_hanh: 'Ủy ban nhân dân tỉnh Đắk Lắk',
      nguoi_ky: 'Hồ Thị Nguyên Thảo',
      trich_yeu: 'Quy định mức tỷ lệ (%) cụ thể để xác định đơn giá thuê đất; mức tỷ lệ (%) để tính tiền thuê đối với đất xây dựng công trình ngầm, đất có mặt nước trên địa bàn tỉnh Đắk Lắk',
      processing_time: 115.27,
      ocr_confidence: 0.978,
      total_stamps: 1,
      tom_tat_ngan: 'Quy định mức tỷ lệ thuê đất trên địa bàn tỉnh Đắk Lắk.',
      diem_chinh: [
        'Mức tỷ lệ thuê đất hàng năm được xác định theo từng khu vực cụ thể.',
        'Đất xây dựng công trình ngầm áp dụng mức tỷ lệ bằng 50% mức thuê đất trên bề mặt.',
      ],
      van_ban_lien_quan: ['Luật Đất đai 2024', 'Nghị định 46/2014/NĐ-CP'],
      tu_khoa: ['Thuê đất', 'Tỷ lệ', 'Đắk Lắk', 'Công trình ngầm'],
      linh_vuc: 'Tài nguyên & Đất đai',
      _confidence: {
        loai_van_ban: 0.99,
        so_hieu: 0.98,
        ngay_ban_hanh: 0.97,
        co_quan_ban_hanh: 0.95,
        nguoi_ky: 0.96,
        trich_yeu: 0.93,
      },
      raw_json: { pages: [{ page: 1 }] },
    },
  },
  {
    id: 3,
    filename: 'nd_30_2020_ND-CP.pdf',
    file_type: 'pdf',
    file_size: 3276800,
    num_pages: 24,
    status: 'completed',
    created_at: '2026-05-08T14:20:00Z',
    extraction: {
      loai_van_ban: 'Nghị định',
      so_hieu: '30/2020/NĐ-CP',
      ngay_ban_hanh: '05/03/2020',
      co_quan_ban_hanh: 'Chính phủ',
      nguoi_ky: 'Nguyễn Xuân Phúc',
      trich_yeu: 'Về công tác văn thư',
      processing_time: 542.18,
      ocr_confidence: 0.951,
      total_stamps: 3,
      tom_tat_ngan: 'Quy định về công tác văn thư trong cơ quan, tổ chức.',
      tom_tat_day_du: 'Nghị định quy định chi tiết về soạn thảo, ban hành, quản lý và lưu trữ văn bản hành chính. Phạm vi điều chỉnh bao gồm thể thức, kỹ thuật trình bày văn bản, quy trình quản lý văn bản đi và đến, quản lý và sử dụng con dấu.',
      diem_chinh: [
        'Quy định 14 ô số thể thức văn bản hành chính chuẩn hóa trên khổ A4.',
        'Bắt buộc sử dụng phông chữ Times New Roman cho văn bản hành chính.',
        'Quy trình quản lý văn bản đi bao gồm 7 bước từ soạn thảo đến lưu hồ sơ.',
      ],
      van_ban_lien_quan: ['Luật Lưu trữ 2011', 'Nghị định 110/2004/NĐ-CP'],
      tu_khoa: ['Văn thư', 'Thể thức', 'Con dấu', 'Quản lý văn bản', 'NĐ 30'],
      linh_vuc: 'Hành chính & Văn thư',
      _confidence: {
        loai_van_ban: 0.99,
        so_hieu: 0.99,
        ngay_ban_hanh: 0.95,
        co_quan_ban_hanh: 0.98,
        nguoi_ky: 0.90,
        trich_yeu: 0.92,
      },
      raw_json: { pages: [{ page: 1 }] },
    },
  },
  {
    id: 4,
    filename: 'tt_15_2025_TT-BYT.pdf',
    file_type: 'pdf',
    file_size: 1536000,
    num_pages: 6,
    status: 'completed',
    created_at: '2026-05-07T10:45:00Z',
    extraction: {
      loai_van_ban: 'Thông tư',
      so_hieu: '15/2025/TT-BYT',
      ngay_ban_hanh: '20/06/2025',
      co_quan_ban_hanh: 'Bộ Y tế',
      nguoi_ky: 'Đỗ Xuân Tuyên',
      trich_yeu: 'Quy định về tiêu chuẩn sức khỏe của người lái xe và việc khám sức khỏe định kỳ cho người lái xe',
      processing_time: 98.54,
      ocr_confidence: 0.982,
      total_stamps: 1,
      tu_khoa: ['Y tế', 'Lái xe', 'Khám sức khỏe', 'Tiêu chuẩn'],
      linh_vuc: 'Y tế',
      _confidence: {
        loai_van_ban: 0.99,
        so_hieu: 0.97,
        ngay_ban_hanh: 0.98,
        co_quan_ban_hanh: 0.96,
        nguoi_ky: 0.94,
        trich_yeu: 0.91,
      },
      raw_json: { pages: [{ page: 1 }] },
    },
  },
  {
    id: 5,
    filename: 'cv_125_BGDDT-VP.pdf',
    file_type: 'pdf',
    file_size: 819200,
    num_pages: 3,
    status: 'completed',
    created_at: '2026-05-06T16:30:00Z',
    extraction: {
      loai_van_ban: 'Công văn',
      so_hieu: '125/BGDĐT-VP',
      ngay_ban_hanh: '15/01/2026',
      co_quan_ban_hanh: 'Bộ Giáo dục và Đào tạo',
      nguoi_ky: 'Nguyễn Kim Sơn',
      trich_yeu: 'Về việc triển khai kế hoạch tuyển sinh đại học năm 2026',
      processing_time: 67.33,
      ocr_confidence: 0.991,
      total_stamps: 1,
      tu_khoa: ['Tuyển sinh', 'Đại học', '2026', 'Giáo dục'],
      linh_vuc: 'Giáo dục & Đào tạo',
      _confidence: {
        loai_van_ban: 0.98,
        so_hieu: 0.99,
        ngay_ban_hanh: 0.97,
        co_quan_ban_hanh: 0.99,
        nguoi_ky: 0.95,
        trich_yeu: 0.88,
      },
      raw_json: { pages: [{ page: 1 }] },
    },
  },
  {
    id: 6,
    filename: 'tb_08_STC.pdf',
    file_type: 'pdf',
    file_size: 614400,
    num_pages: 2,
    status: 'completed',
    created_at: '2026-05-05T11:00:00Z',
    extraction: {
      loai_van_ban: 'Thông báo',
      so_hieu: '08/TB-STC',
      ngay_ban_hanh: '05/01/2026',
      co_quan_ban_hanh: 'Sở Tài chính tỉnh Bình Dương',
      nguoi_ky: 'Lê Văn Minh',
      trich_yeu: 'Thông báo về mức thu phí và lệ phí mới áp dụng từ ngày 01/02/2026',
      processing_time: 52.17,
      ocr_confidence: 0.988,
      total_stamps: 1,
      tu_khoa: ['Phí', 'Lệ phí', 'Tài chính', 'Bình Dương'],
      linh_vuc: 'Tài chính',
      _confidence: {
        loai_van_ban: 0.97,
        so_hieu: 0.96,
        ngay_ban_hanh: 0.99,
        co_quan_ban_hanh: 0.93,
        nguoi_ky: 0.91,
        trich_yeu: 0.87,
      },
      raw_json: { pages: [{ page: 1 }] },
    },
  },
  {
    id: 7,
    filename: 'huong_dan_scan.png',
    file_type: 'image',
    file_size: 4096000,
    num_pages: 1,
    status: 'failed',
    created_at: '2026-05-04T09:15:00Z',
    extraction: null,
  },
  {
    id: 8,
    filename: 'bc_quy1_2026_UBND_HN.pdf',
    file_type: 'pdf',
    file_size: 5120000,
    num_pages: 18,
    status: 'processing',
    created_at: '2026-05-09T10:00:00Z',
    extraction: null,
  },
]

// ═══════════════════════════════════════════════════════════════
// Benchmark Metrics (from real research_metrics.json)
// ═══════════════════════════════════════════════════════════════

export const MOCK_BENCHMARK = {
  metadata: {
    timestamp: '2026-05-09T19:00:09',
    pipeline: 'VietIDP OCR-LLM Pipeline v5.1',
    ocr_engine: 'EasyOCR + VietOCR vgg_transformer',
    llm_model: 'qwen2.5:7b',
    llm_temperature: 0.0,
    ocr_dpi: 400,
    stamp_detector: 'YOLOv8x',
    stamp_matting: 'HybridStampMatting',
    gpu: 'NVIDIA RTX 5070',
  },
  document_level: {
    total_documents: 100,
    perfect_documents: 6,
    perfect_rate: 0.06,
  },
  field_level: {
    loai_van_ban: { exact_match: 0.85, token_f1: 0.865, char_sim: 0.889, correct: 85, wrong: 15, missed: 0 },
    so_hieu: { exact_match: 0.50, token_f1: 0.500, char_sim: 0.704, correct: 50, wrong: 47, missed: 3 },
    ngay_ban_hanh: { exact_match: 0.72, token_f1: 0.720, char_sim: 0.885, correct: 72, wrong: 27, missed: 1 },
    co_quan_ban_hanh: { exact_match: 0.59, token_f1: 0.736, char_sim: 0.732, correct: 59, wrong: 41, missed: 0 },
    trich_yeu: { exact_match: 0.15, token_f1: 0.648, char_sim: 0.630, correct: 15, wrong: 82, missed: 3 },
    nguoi_ky: { exact_match: 0.46, token_f1: 0.618, char_sim: 0.665, correct: 46, wrong: 50, missed: 4 },
  },
  macro_averages: {
    exact_match: 0.545,
    token_f1: 0.681,
    char_similarity: 0.751,
  },
  processing_time: {
    total_seconds: 61182.78,
    mean_seconds: 611.83,
    min_seconds: 46.86,
    max_seconds: 8810.74,
  },
}

export const MOCK_PROFILER = {
  total_time_s: 27.354,
  peak_vram_mb: 2425.0,
  stages: [
    { stage: 'Load Image', latency_s: 0.086, vram_peak_mb: 0 },
    { stage: 'YOLO Detection', latency_s: 1.651, vram_peak_mb: 63.7 },
    { stage: 'Stamp Matting', latency_s: 2.551, vram_peak_mb: 11.7 },
    { stage: 'OCR (VietOCR + EasyOCR)', latency_s: 15.228, vram_peak_mb: 2425.0 },
    { stage: 'LLM (Qwen2.5-7B)', latency_s: 7.838, vram_peak_mb: 285.9 },
  ],
}

// ═══════════════════════════════════════════════════════════════
// Mock System Health (matches GET /api/health)
// ═══════════════════════════════════════════════════════════════

export const MOCK_HEALTH = {
  status: 'healthy',
  services: {
    database: 'active',
    ollama: 'active',
    model: 'qwen2.5:7b',
    yolo: 'standby',
    vietocr: 'standby',
    gpu: 'active',
    gpu_name: 'NVIDIA RTX 5070',
    gpu_vram: '8GB',
  },
}

// ═══════════════════════════════════════════════════════════════
// Mock Chat Responses
// ═══════════════════════════════════════════════════════════════

export const MOCK_CHAT_RESPONSES = {
  vi: [
    { q: 'Ai là người ký văn bản này?', a: 'Người ký văn bản là **Nguyễn Chí Dũng**, với chức danh Bộ trưởng Bộ Kế hoạch và Đầu tư, ký thay Thủ tướng Chính phủ theo ủy quyền.' },
    { q: 'Văn bản này có hiệu lực từ ngày nào?', a: 'Quyết định này có hiệu lực thi hành kể từ ngày **01/03/2026**, tức là sau 60 ngày kể từ ngày ban hành (07/01/2026).' },
    { q: 'Tóm tắt nội dung chính?', a: 'Quyết định sửa đổi, bổ sung các thủ tục hành chính thuộc Bộ KH&CN, bao gồm:\n1. Giảm 30% thời gian xử lý\n2. Chuyển 15 thủ tục sang trực tuyến\n3. Bãi bỏ yêu cầu bản sao chứng thực cho 8 loại giấy tờ\n4. Áp dụng cơ chế một cửa liên thông' },
  ],
  en: [
    { q: 'Who signed this document?', a: 'The document was signed by **Nguyễn Chí Dũng**, Minister of Planning and Investment, signing on behalf of the Prime Minister by authorization.' },
    { q: 'When does this take effect?', a: 'This Decision takes effect from **March 1, 2026**, which is 60 days after the date of issuance (January 7, 2026).' },
    { q: 'Summarize the main content?', a: 'The Decision amends administrative procedures under the Ministry of Science and Technology, including:\n1. 30% reduction in processing time\n2. Converting 15 procedures to fully online\n3. Eliminating certified copy requirements for 8 document types\n4. Implementing one-stop-shop mechanism' },
  ],
}

export const MOCK_SUGGESTED_QUESTIONS = {
  vi: [
    'Ai là người ký văn bản này?',
    'Văn bản có hiệu lực từ ngày nào?',
    'Tóm tắt nội dung chính?',
    'Văn bản này liên quan đến luật nào?',
    'Cơ quan nào chịu trách nhiệm thi hành?',
  ],
  en: [
    'Who signed this document?',
    'When does this take effect?',
    'Summarize the main content?',
    'What laws does this reference?',
    'Which agency is responsible?',
  ],
}

// ═══════════════════════════════════════════════════════════════
// Mock Processing Logs
// ═══════════════════════════════════════════════════════════════

export const MOCK_PROCESSING_STAGES = [
  { key: 'upload', progress: 5, message: 'File received: qd_02_2026_QD-TTg.pdf (2.3 MB)' },
  { key: 'preprocess', progress: 15, message: 'Preprocessing: Deskew -0.8° | Denoise applied' },
  { key: 'stamp', progress: 30, message: 'YOLO detected 2 stamps (conf: 94%, 89%)' },
  { key: 'matting', progress: 40, message: 'HybridStampMatting: Removed 2 stamps successfully' },
  { key: 'ocr_detect', progress: 55, message: 'EasyOCR: Detected 247 text regions' },
  { key: 'ocr_recognize', progress: 70, message: 'VietOCR: Recognized 247/247 regions (conf: 96.5%)' },
  { key: 'layout', progress: 78, message: 'NĐ30 Layout: Classified 14 regions' },
  { key: 'llm', progress: 90, message: 'Qwen2.5-7B: Extracting 6 fields...' },
  { key: 'validate', progress: 95, message: 'Schema validation passed | Regex enrichment: 2 overrides' },
  { key: 'complete', progress: 100, message: 'Pipeline complete! 374.06s total' },
]

// ═══════════════════════════════════════════════════════════════
// Helper: Check if backend is available
// ═══════════════════════════════════════════════════════════════

let _mockMode = null

export async function isMockMode() {
  if (_mockMode !== null) return _mockMode
  try {
    const res = await fetch('/api/health', { signal: AbortSignal.timeout(2000) })
    _mockMode = !res.ok
  } catch {
    _mockMode = true
  }
  return _mockMode
}

export function forceMockMode(enabled = true) {
  _mockMode = enabled
}

// Get the primary mock document (for workspace demo)
export function getMockDocument(id) {
  return MOCK_DOCUMENTS.find(d => d.id === Number(id)) || MOCK_DOCUMENTS[0]
}

// Get documents list matching API format
export function getMockDocumentsList() {
  return {
    documents: MOCK_DOCUMENTS,
    total: MOCK_DOCUMENTS.length,
  }
}
