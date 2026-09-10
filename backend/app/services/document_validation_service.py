import io
import fitz
from PIL import Image
from app.schemas.document import FileValidation
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class DocumentValidationService:
    def validate(self, file_content: bytes, filename: str, content_type: str) -> FileValidation:
        ext = '.' + filename.split('.')[-1].lower() if '.' in filename else ''
        
        is_supported = ext in settings.ALLOWED_EXTENSIONS and content_type in settings.ALLOWED_MIME_TYPES
        
        if not is_supported:
            return FileValidation(
                file_name=filename,
                file_type=content_type,
                is_supported=False,
                is_readable=False,
                status='FAIL',
                message='Unsupported file extension or MIME type'
            )
            
        if len(file_content) == 0:
            return FileValidation(
                file_name=filename,
                file_type=content_type,
                is_supported=True,
                is_readable=False,
                status='FAIL',
                message='File is empty'
            )

        try:
            page_count = None
            is_readable = False
            
            if content_type == 'application/pdf':
                doc = fitz.open(stream=file_content, filetype="pdf")
                page_count = doc.page_count
                is_readable = True
                doc.close()
                if page_count > settings.MAX_PAGES:
                    return FileValidation(
                        file_name=filename, file_type=content_type,
                        is_supported=True, is_readable=True, page_count=page_count,
                        status='FAIL', message=f'Exceeds maximum page count of {settings.MAX_PAGES}'
                    )
            elif content_type in ['image/jpeg', 'image/png']:
                img = Image.open(io.BytesIO(file_content))
                img.verify()
                page_count = 1
                is_readable = True
                
            return FileValidation(
                file_name=filename, file_type=content_type,
                is_supported=True, is_readable=is_readable, page_count=page_count,
                status='PASS'
            )
        except Exception as e:
            logger.error(f'Validation failed for {filename}: {str(e)}')
            return FileValidation(
                file_name=filename, file_type=content_type,
                is_supported=True, is_readable=False,
                status='FAIL', message=f'File is corrupted or unreadable: {str(e)}'
            )
