const express = require('express');
const multer = require('multer');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const app = express();

// Security: Restrict CORS to localhost only
app.use(cors({
  origin: ['http://localhost:3000', 'http://localhost:5173'],
  methods: ['GET', 'POST'],
}));

app.use(express.json({ limit: '20mb' }));

// Setup thư mục lưu file tạm
const uploadDir = path.join(__dirname, 'uploads');
if (!fs.existsSync(uploadDir)) fs.mkdirSync(uploadDir);

// Phục vụ thư mục uploads như file tĩnh
app.use('/uploads', express.static(uploadDir));

const storage = multer.diskStorage({
  destination: (req, file, cb) => cb(null, uploadDir),
  filename: (req, file, cb) => cb(null, Date.now() + '-' + file.originalname)
});

// File size limit: 20MB
const upload = multer({
  storage,
  limits: { fileSize: 20 * 1024 * 1024 }
});

// API để Upload file + detect stamps
app.post('/api/process', upload.single('document'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded' });

  const filePath = req.file.path;
  const scriptPath = path.join(__dirname, '../../scripts/detect_api.py');

  const pythonProcess = spawn('python', [scriptPath, filePath]);

  let pythonOut = '';
  pythonProcess.stdout.on('data', (data) => {
    pythonOut += data.toString();
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python Error: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    try {
      let cleanOut = pythonOut.trim();
      const firstBrace = cleanOut.indexOf('{');
      const lastBrace = cleanOut.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace !== -1) {
        cleanOut = cleanOut.substring(firstBrace, lastBrace + 1);
      }
      const result = JSON.parse(cleanOut);

      const baseUrl = process.env.RENDER_EXTERNAL_URL || `${req.protocol}://${req.get('host')}`;

      const processedPages = (result.pages || []).map(page => {
        return {
          img_w: page.img_w,
          img_h: page.img_h,
          stamps: page.stamps,
          original_url: page.original_image ? `${baseUrl}/uploads/${path.basename(page.original_image)}` : null,
          annotated_url: page.output_image ? `${baseUrl}/uploads/${path.basename(page.output_image)}` : null
        };
      });

      res.json({
        success: true,
        pages: processedPages,
        confidence_avg: result.confidence_avg,
        summary: result.summary || null,
        extracted_text: result.extracted_text || ''
      });

    } catch (e) {
      console.error('Parse error:', e.message);
      res.status(500).json({ error: 'Failed to process document with AI' });
    }
  });
});

// API Tóm tắt văn bản dùng Ollama + Qwen2.5
app.post('/api/summarize', upload.single('document'), (req, res) => {
  if (!req.file) return res.status(400).json({ error: 'No file uploaded' });

  const filePath = req.file.path;
  const scriptPath = path.join(__dirname, '../../scripts/summarize.py');

  const pythonProcess = spawn('python', [scriptPath, filePath]);

  let pythonOut = '';
  pythonProcess.stdout.on('data', (data) => { pythonOut += data.toString(); });
  pythonProcess.stderr.on('data', (data) => { console.error(`Summarize Error: ${data}`); });

  pythonProcess.on('close', () => {
    try { fs.unlinkSync(filePath); } catch {}
    try {
      let cleanOut = pythonOut.trim();
      const firstBrace = cleanOut.indexOf('{');
      const lastBrace = cleanOut.lastIndexOf('}');
      if (firstBrace !== -1 && lastBrace !== -1) {
        cleanOut = cleanOut.substring(firstBrace, lastBrace + 1);
      }
      const result = JSON.parse(cleanOut);
      if (result.error) return res.status(500).json({ error: result.error });
      res.json(result);
    } catch (e) {
      console.error('Parse error:', e.message);
      res.status(500).json({ error: 'Lỗi khi phân tích kết quả từ AI' });
    }
  });
});

// API Chatbot hỏi đáp
app.post('/api/chat', (req, res) => {
  const { question, context } = req.body;
  if (!question || !context) return res.status(400).json({ error: 'Thiếu question hoặc context' });

  const payload = JSON.stringify({
    model: 'qwen2.5:1.5b',
    messages: [
      {
        role: "system",
        content: "Bạn là chuyên gia phân tích văn bản. Hãy đọc kỹ tài liệu được cung cấp và trả lời câu hỏi của người dùng TRỰC TIẾP dựa vào văn bản. Bắt buộc: 1) KHÔNG được tự nghĩ ra. 2) Cố gắng trích xuất đầy đủ và chính xác (ngày tháng, số hiệu, nội dung). 3) Trả lời ngắn gọn bằng tiếng Việt. Nếu tài liệu không chứa thông tin, hãy nói 'Tôi không tìm thấy'."
      },
      {
        role: "user",
        content: `[TÀI LIỆU VĂN BẢN]\n${context}\n\n[CÂU HỎI CỦA NGƯỜI DÙNG]\n${question}`
      }
    ],
    stream: true,
    options: {
      temperature: 0.1,
      top_p: 0.3,
    }
  });

  const options = {
    hostname: '127.0.0.1',
    port: 11434,
    path: '/api/chat',
    method: 'POST',
    headers: { 'Content-Type': 'application/json' }
  };

  const ollamaReq = require('http').request(options, (ollamaRes) => {
    let data = '';
    ollamaRes.on('data', chunk => { data += chunk; });
    ollamaRes.on('end', () => {
      try {
        const lines = data.trim().split('\n');
        let fullResponse = '';
        lines.forEach(line => {
          if (line) fullResponse += JSON.parse(line).message.content;
        });
        res.json({ answer: fullResponse });
      } catch (err) {
        res.status(500).json({ error: 'Ollama parse error' });
      }
    });
  });

  ollamaReq.on('error', (e) => res.status(500).json({ error: e.message }));
  ollamaReq.write(payload);
  ollamaReq.end();
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', version: '2.0.0' });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 VietIDP Backend v2.0 đang chạy ở port ${PORT}`);
});
