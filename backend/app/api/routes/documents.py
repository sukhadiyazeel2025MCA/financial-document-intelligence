import json
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.document import DocumentResponse, DocumentListItem
from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.core.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix='/api/v1')

@router.get('/health')
async def health_check():
    return {'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}

@router.post('/documents/process', response_model=DocumentResponse)
async def process_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    db: Session = Depends(get_db)
):
    valid_types = ['invoice', 'balance_sheet', 'profit_and_loss', 'cash_flow_statement']
    if document_type not in valid_types:
        raise HTTPException(400, detail={'error': {'code': 'INVALID_DOCUMENT_TYPE', 'message': f'Must be one of: {valid_types}'}})
    
    file_content = await file.read()
    service = DocumentService(db)
    result = service.process_document(file_content, file.filename, file.content_type, document_type)
    return result

@router.get('/documents/id/{document_id}', response_model=DocumentResponse)
async def get_document_by_id(document_id: int, db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    doc = repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(404, detail={'error': {'code': 'DOCUMENT_NOT_FOUND', 'message': f'No processed document found with ID: {document_id}'}})
    return _db_record_to_response(doc)

@router.get('/documents/{document_name}', response_model=DocumentResponse)
async def get_document(document_name: str, db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    doc = repo.get_by_name(document_name)
    if not doc:
        raise HTTPException(404, detail={'error': {'code': 'DOCUMENT_NOT_FOUND', 'message': f'No processed document found with name: {document_name}'}})
    return _db_record_to_response(doc)

@router.get('/documents', response_model=list[DocumentListItem])
async def list_documents(db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    docs = repo.list_all()
    res = []
    for d in docs:
        iso_str = d.created_at.isoformat()
        if not iso_str.endswith('Z') and '+' not in iso_str:
            iso_str += 'Z'
        res.append(DocumentListItem(
            id=d.id,
            document_name=d.document_name,
            document_type=d.document_type,
            processing_status=d.processing_status,
            overall_confidence=d.overall_confidence,
            created_at=iso_str
        ))
    return res

@router.delete('/documents/{document_id}')
async def delete_document(document_id: int, db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    success = repo.delete_by_id(document_id)
    if not success:
        raise HTTPException(404, detail={'error': {'code': 'NOT_FOUND', 'message': f'Document {document_id} not found'}})
    return {'message': f'Document {document_id} deleted successfully'}

@router.delete('/documents')
async def clear_all_documents(db: Session = Depends(get_db)):
    repo = DocumentRepository(db)
    count = repo.delete_all()
    return {'message': f'Successfully cleared {count} processed document(s)'}

def _db_record_to_response(doc) -> DocumentResponse:
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
