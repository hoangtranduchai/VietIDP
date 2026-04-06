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
  const scriptPath = path.join(__dirname, '../ai/detect_api.py');

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
        summary: result.summary || null
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
  const scriptPath = path.join(__dirname, '../ai/summarize.py');

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

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', version: '2.0.0' });
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`🚀 VietIDP Backend v2.0 đang chạy ở port ${PORT}`);
});
