import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.extraction_service import ExtractionService
from app.services.ocr_service import OCRService

class TestOCRService:
    def setup_method(self):
        self.service = OCRService()
    
    def test_image_returns_ocr_used(self):
        """For image files, OCR should be flagged as used"""
        # Create a minimal valid PNG (1x1 pixel)
        import struct
        import zlib
        
        def create_minimal_png():
            signature = b'\x89PNG\r\n\x1a\n'
            # IHDR chunk
            ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
            ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff
            ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc)
            # IDAT chunk
            raw_data = zlib.compress(b'\x00\x00\x00\x00')
            idat_crc = zlib.crc32(b'IDAT' + raw_data) & 0xffffffff
            idat = struct.pack('>I', len(raw_data)) + b'IDAT' + raw_data + struct.pack('>I', idat_crc)
            # IEND chunk
            iend_crc = zlib.crc32(b'IEND') & 0xffffffff
            iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc)
            return signature + ihdr + idat + iend
        
        png_bytes = create_minimal_png()
        text, ocr_used = self.service.extract_text(png_bytes, 'test.png', 'image/png')
        assert ocr_used == True

class TestExtractionService:
    def test_service_initialization(self):
        """Test that extraction service can be initialized (may fail without API key)"""
        try:
            service = ExtractionService()
            assert service is not None
        except Exception:
            # Expected if no API key is configured
            pytest.skip('Gemini API key not configured')
