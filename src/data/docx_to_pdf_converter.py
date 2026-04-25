import os
import glob
import random
import logging
from pathlib import Path
from multiprocessing import Pool
import fitz  # PyMuPDF
from PIL import Image

try:
    from docx2pdf import convert
except ImportError:
    print("[LỖI] Thiếu thư viện docx2pdf. Cài đặt bằng lệnh: pip install docx2pdf")
    exit(1)

# ==============================================================================
# CẤU HÌNH LOGGING
# ==============================================================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

class DocxToPdfImageConverter:
    def __init__(self, raw_docx_dir: str, output_dir: str, stamps_dir: str = None):
        """
        Khởi tạo Converter.
        :param raw_docx_dir: Thư mục chứa các file .docx
        :param output_dir: Thư mục lưu kết quả (pdf, clean_images, stamped_images)
        :param stamps_dir: Thư mục chứa ảnh con dấu (để tạo ảnh nhiễu cho GAN)
        """
        self.raw_docx_dir = Path(raw_docx_dir)
        self.output_dir = Path(output_dir)
        self.stamps_dir = Path(stamps_dir) if stamps_dir else None

        self.pdf_dir = self.output_dir / "pdfs"
        self.clean_img_dir = self.output_dir / "clean_images"
        self.stamped_img_dir = self.output_dir / "stamped_images"

        # Tạo cây thư mục
        for d in [self.pdf_dir, self.clean_img_dir, self.stamped_img_dir]:
            d.mkdir(parents=True, exist_ok=True)

        self.stamps = self._load_stamps()

    def _load_stamps(self):
        if not self.stamps_dir or not self.stamps_dir.exists():
            logging.warning("Không tìm thấy thư mục stamps. Bỏ qua bước tạo ảnh có dấu.")
            return []
        
        stamp_files = list(self.stamps_dir.glob("*.png"))
        if not stamp_files:
            logging.warning("Thư mục stamps rỗng.")
        else:
            logging.info(f"Đã tải {len(stamp_files)} mẫu con dấu.")
        return stamp_files

    def convert_all_docx_to_pdf(self):
        """Chuyển đổi toàn bộ DOCX sang PDF (Sử dụng docx2pdf qua MS Word)"""
        logging.info("BẮT ĐẦU CHUYỂN ĐỔI DOCX -> PDF...")
        docx_files = list(self.raw_docx_dir.rglob("*.docx"))
        
        if not docx_files:
            logging.error(f"Không tìm thấy file .docx nào trong {self.raw_docx_dir}")
            return
            
        logging.info(f"Đã tìm thấy {len(docx_files)} file .docx")
        
        # docx2pdf directory mode không quét thư mục con (recursive). 
        # Do đó, dùng win32com trực tiếp để tối ưu mở Word 1 lần duy nhất cho toàn bộ batch.
        try:
            import win32com.client
            import pythoncom
            from tqdm import tqdm
            
            pythoncom.CoInitialize()
            word = win32com.client.DispatchEx("Word.Application")
            word.Visible = False
            
            for docx in tqdm(docx_files, desc="Converting to PDF"):
                # Để tránh trùng tên, ta có thể dùng cả thư mục cha hoặc chỉ lưu stem (nếu file 2000 mẫu đã unique)
                out_pdf = self.pdf_dir / f"{docx.parent.name}_{docx.stem}.pdf"
                
                if not out_pdf.exists():
                    try:
                        doc = word.Documents.Open(str(docx.resolve()))
                        doc.SaveAs(str(out_pdf.resolve()), FileFormat=17) # 17 = wdFormatPDF
                        doc.Close(0)
                    except Exception as e:
                        logging.error(f" Lỗi convert {docx.name}: {e}")
            word.Quit()
        except Exception as e:
            logging.warning(f"Không dùng được win32com ({e}), chuyển sang fallback bằng docx2pdf lẻ...")
            from tqdm import tqdm
            for docx in tqdm(docx_files, desc="Converting to PDF"):
                out_pdf = self.pdf_dir / f"{docx.parent.name}_{docx.stem}.pdf"
                if not out_pdf.exists():
                    convert(str(docx), str(out_pdf))
                    
        logging.info("HOÀN THÀNH CHUYỂN ĐỔI DOCX -> PDF.")

    def pdf_to_images(self, dpi: int = 200):
        """Render các file PDF thành ảnh PNG sạch (Clean)"""
        logging.info("BẮT ĐẦU CHUYỂN ĐỔI PDF -> CLEAN IMAGES...")
        pdf_files = list(self.pdf_dir.glob("*.pdf"))
        
        for pdf_path in pdf_files:
            try:
                doc = fitz.open(pdf_path)
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    pix = page.get_pixmap(dpi=dpi)
                    
                    img_name = f"{pdf_path.stem}_page_{page_num+1}.png"
                    img_path = self.clean_img_dir / img_name
                    pix.save(str(img_path))
                    
                    # Nếu có stamps, tự động sinh luôn ảnh bị đóng dấu (Noisy)
                    if self.stamps:
                        self._create_stamped_version(img_path)
            except Exception as e:
                logging.error(f"Lỗi khi xử lý {pdf_path.name}: {e}")
                
        logging.info("HOÀN THÀNH CHUYỂN ĐỔI PDF -> IMAGES.")

    def _create_stamped_version(self, clean_img_path: Path):
        """Overlay ngẫu nhiên 1-2 con dấu lên ảnh sạch để tạo ảnh Noisy cho GAN"""
        try:
            base_img = Image.open(clean_img_path).convert("RGBA")
            
            # Đóng 1 hoặc 2 dấu
            num_stamps = random.choices([1, 2], weights=[80, 20])[0]
            
            for _ in range(num_stamps):
                stamp_path = random.choice(self.stamps)
                stamp_img = Image.open(stamp_path).convert("RGBA")
                
                # Resize stamp sao cho tỷ lệ hợp lý với văn bản A4 (khoảng 15-25% chiều rộng ảnh)
                scale_factor = random.uniform(0.15, 0.25)
                new_width = int(base_img.width * scale_factor)
                aspect_ratio = stamp_img.height / stamp_img.width
                new_height = int(new_width * aspect_ratio)
                
                stamp_img = stamp_img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Random vị trí: Thường con dấu nằm ở 1/3 dưới cùng bên phải hoặc giữa ảnh
                max_x = base_img.width - new_width
                max_y = base_img.height - new_height
                
                # Trọng số vị trí: Đa số ở bên phải, nửa dưới
                x = random.randint(int(max_x * 0.4), max_x - 10)
                y = random.randint(int(max_y * 0.5), max_y - 10)
                
                # Composite
                base_img.alpha_composite(stamp_img, dest=(x, y))
            
            # Lưu lại dạng RGB để giảm dung lượng
            stamped_path = self.stamped_img_dir / clean_img_path.name
            base_img.convert("RGB").save(stamped_path, "PNG")
            
        except Exception as e:
            logging.error(f"Lỗi khi overlay stamp lên {clean_img_path.name}: {e}")

    def run_pipeline(self):
        logging.info("🚀 KHỞI ĐỘNG DATA PREPARATION PIPELINE...")
        self.convert_all_docx_to_pdf()
        self.pdf_to_images()
        logging.info("✅ HOÀN THÀNH PIPELINE CHUẨN BỊ DỮ LIỆU PHASE 1.")

if __name__ == "__main__":
    # Cấu hình đường dẫn
    ROOT_DIR = Path(__file__).resolve().parent.parent.parent
    RAW_DOCX_DIR = ROOT_DIR / "data" / "raw_word_files"
    PROCESSED_DIR = ROOT_DIR / "data" / "processed"
    STAMPS_DIR = ROOT_DIR / "data" / "stamps" / "synthetic"
    
    # Tạo thư mục test dummy nếu chưa có để script không báo lỗi
    RAW_DOCX_DIR.mkdir(parents=True, exist_ok=True)
    STAMPS_DIR.mkdir(parents=True, exist_ok=True)
    
    converter = DocxToPdfImageConverter(
        raw_docx_dir=RAW_DOCX_DIR,
        output_dir=PROCESSED_DIR,
        stamps_dir=STAMPS_DIR
    )
    
    converter.run_pipeline()
