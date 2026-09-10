from pydantic import BaseModel, ConfigDict
from typing import Optional, Any

class FileValidation(BaseModel):
    file_name: str
    file_type: str
    is_supported: bool
    is_readable: bool
    page_count: Optional[int] = None
    status: str
    message: Optional[str] = None

class ValidationCheck(BaseModel):
    name: str
    formula: str
    operands: dict
    calculated_value: Optional[float] = None
    reported_value: Optional[float] = None
    variance: Optional[float] = None
    status: str
    message: Optional[str] = None

class ValidationResult(BaseModel):
    checks: list[ValidationCheck] = []
    overall_status: str = 'PASS'
    issues: list[str] = []

class ProcessingMetadata(BaseModel):
    ocr_used: bool = False
    ocr_engine: Optional[str] = None
    ai_model: Optional[str] = None
    processed_at: str
    processing_time_ms: int

class DocumentResponse(BaseModel):
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float] = None
    file_validation: FileValidation
    extracted_data: dict
    validation: ValidationResult
    processing_metadata: ProcessingMetadata

    model_config = ConfigDict(from_attributes=True)

class DocumentListItem(BaseModel):
    id: int
    document_name: str
    document_type: str
    processing_status: str
    overall_confidence: Optional[float] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)

class ErrorResponse(BaseModel):
    error: dict
