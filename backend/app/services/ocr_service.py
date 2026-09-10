import fitz
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class OCRService:
    def extract_text(self, file_content: bytes, filename: str, content_type: str) -> tuple[str, bool]:
        if content_type == 'application/pdf':
            try:
                doc = fitz.open(stream=file_content, filetype="pdf")
                text = ""
                for page in doc:
                    text += page.get_text()
                page_count = doc.page_count
                doc.close()
                
                if len(text.strip()) > page_count * 50:
                    logger.info(f"Extracted sufficient text from PDF: {filename}")
                    return text, False
                else:
                    logger.info(f"Sparse text in PDF, will use vision model: {filename}")
                    return "", True
            except Exception as e:
                logger.error(f"Text extraction failed for {filename}: {str(e)}")
                return "", True
        else:
            return "", True

    def get_document_images(self, file_content: bytes, filename: str, content_type: str) -> list[bytes]:
        images = []
        if content_type == 'application/pdf':
            try:
                doc = fitz.open(stream=file_content, filetype="pdf")
                for page in doc:
                    # 1.5x zoom provides optimal OCR balance without massive megabyte payloads
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
                    images.append(pix.tobytes("jpeg", jpg_quality=85))
                doc.close()
            except Exception as e:
                logger.error(f"Image generation failed for {filename}: {str(e)}")
        else:
            images.append(file_content)
            
        return images
