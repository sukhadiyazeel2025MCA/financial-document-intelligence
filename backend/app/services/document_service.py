import time
import json
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.document_repository import DocumentRepository
from app.services.document_validation_service import DocumentValidationService
from app.services.ocr_service import OCRService
from app.services.extraction_service import ExtractionService
from app.services.financial_validation_service import FinancialValidationService
from app.schemas.document import DocumentResponse, ProcessingMetadata
from app.core.logging_config import get_logger

logger = get_logger(__name__)

class DocumentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DocumentRepository(db)
        self.validator = DocumentValidationService()
        self.ocr = OCRService()
        self.extractor = ExtractionService()
        self.fin_validator = FinancialValidationService()

    def process_document(self, file_content: bytes, filename: str, content_type: str, document_type: str) -> DocumentResponse:
        start_time = time.time()
        file_val = self.validator.validate(file_content, filename, content_type)
        
        if file_val.status == 'FAIL':
            # Save failed doc
            doc = self.repo.save(
                document_name=filename, document_type=document_type, processing_status='FAILED',
                file_validation=file_val.model_dump(), extracted_data={},
                validation_result={'checks': [], 'overall_status': 'FAIL', 'issues': []},
                processing_metadata={'processed_at': datetime.utcnow().isoformat(), 'processing_time_ms': int((time.time()-start_time)*1000)},
                overall_confidence=None
            )
            return self._build_response(doc)

        try:
            text, ocr_used = self.ocr.extract_text(file_content, filename, content_type)
            # Only generate and upload image payloads if text is not available (i.e. scanned image / non-extractable PDF)
            images = self.ocr.get_document_images(file_content, filename, content_type) if ocr_used else []
            
            # Intelligent type correction if user left default 'invoice' for a balance sheet or financial statement
            detected_type = self._detect_document_type(filename, text, document_type)
            if detected_type != document_type:
                logger.info(f"Auto-corrected document_type from '{document_type}' to '{detected_type}' for '{filename}'")
                document_type = detected_type

            extracted_data = self.extractor.extract(text, images, document_type, filename)
            fin_val_result = self.fin_validator.validate(extracted_data, document_type)
            
            proc_time_ms = int((time.time() - start_time) * 1000)
            meta = ProcessingMetadata(
                ocr_used=ocr_used,
                ocr_engine='fitz/gemini' if ocr_used else 'fitz',
                ai_model=getattr(self.extractor, 'model_name', 'gemini-3.6-flash'),
                processed_at=datetime.utcnow().isoformat(),
                processing_time_ms=proc_time_ms
            )

            # Calculate overall confidence based on extracted field completeness and validation checks
            confidences = []
            def extract_conf(d):
                if isinstance(d, dict):
                    if 'confidence' in d and isinstance(d['confidence'], (int, float)):
                        confidences.append(float(d['confidence']))
                    for k, v in d.items():
                        extract_conf(v)
                elif isinstance(d, list):
                    for i in d:
                        extract_conf(i)
            extract_conf(extracted_data)

            if confidences:
                overall_confidence = round(sum(confidences) / len(confidences), 2)
            else:
                # Estimate confidence from populated key fields vs expected fields and validation outcome
                non_empty = sum(1 for v in extracted_data.values() if v is not None and v != "" and v != [])
                total_fields = max(len(extracted_data), 1)
                completeness = min(non_empty / total_fields, 1.0)
                val_boost = 0.15 if fin_val_result.overall_status == 'PASS' else 0.0
                overall_confidence = round(min(0.80 + (completeness * 0.15) + val_boost, 0.99), 2)

            doc = self.repo.save(
                document_name=filename, document_type=document_type, processing_status='PASS',
                file_validation=file_val.model_dump(), extracted_data=extracted_data,
                validation_result=fin_val_result.model_dump(), processing_metadata=meta.model_dump(),
                overall_confidence=overall_confidence
            )
            return self._build_response(doc)

        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            proc_time_ms = int((time.time() - start_time) * 1000)
            doc = self.repo.save(
                document_name=filename, document_type=document_type, processing_status='FAILED',
                file_validation=file_val.model_dump(), extracted_data={},
                validation_result={'checks': [], 'overall_status': 'FAIL', 'issues': [str(e)]},
                processing_metadata={'processed_at': datetime.utcnow().isoformat(), 'processing_time_ms': proc_time_ms},
                overall_confidence=None
            )
            return self._build_response(doc)

    def _build_response(self, doc) -> DocumentResponse:
        return DocumentResponse(
            document_name=doc.document_name,
            document_type=doc.document_type,
            processing_status=doc.processing_status,
            overall_confidence=doc.overall_confidence,
            file_validation=json.loads(doc.file_validation) if isinstance(doc.file_validation, str) else doc.file_validation,
            extracted_data=json.loads(doc.extracted_data) if isinstance(doc.extracted_data, str) else doc.extracted_data,
            validation=json.loads(doc.validation_result) if isinstance(doc.validation_result, str) else doc.validation_result,
            processing_metadata=json.loads(doc.processing_metadata) if isinstance(doc.processing_metadata, str) else doc.processing_metadata
        )

    def _detect_document_type(self, filename: str, text: str, original_type: str) -> str:
        fn = filename.lower()
        txt = (text or "").lower()
        combined = f"{fn} {txt[:1000]}"
        
        # If user explicitly selected something other than default invoice, or filename/content strongly indicates type
        if "balance sheet" in combined or "balance_sheet" in fn or "capital and liabilities" in txt:
            return "balance_sheet"
        if "cash flow" in combined or "cash_flow" in fn or "cash flows" in txt:
            return "cash_flow_statement"
        if "profit and loss" in combined or "p&l" in combined or "income statement" in combined or "statement of profit" in txt:
            return "profit_and_loss"
        if "invoice" in combined or "bill to" in txt or "tax invoice" in txt:
            return "invoice"
            
        return original_type
