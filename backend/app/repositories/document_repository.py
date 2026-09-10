import json
from sqlalchemy.orm import Session
from app.models.document import ProcessedDocument

class DocumentRepository:
    def __init__(self, db: Session):
        self.db = db

    def save(self, document_name: str, document_type: str, processing_status: str, 
             file_validation: dict, extracted_data: dict, validation_result: dict, 
             processing_metadata: dict, overall_confidence: float | None) -> ProcessedDocument:
        doc = ProcessedDocument(
            document_name=document_name,
            document_type=document_type,
            processing_status=processing_status,
            file_validation=json.dumps(file_validation),
            extracted_data=json.dumps(extracted_data),
            validation_result=json.dumps(validation_result),
            processing_metadata=json.dumps(processing_metadata),
            overall_confidence=overall_confidence
        )
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        return doc

    def get_by_name(self, document_name: str) -> ProcessedDocument | None:
        return self.db.query(ProcessedDocument).filter(
            ProcessedDocument.document_name == document_name
        ).order_by(ProcessedDocument.created_at.desc()).first()

    def list_all(self) -> list[ProcessedDocument]:
        return self.db.query(ProcessedDocument).order_by(ProcessedDocument.created_at.desc()).all()

    def get_by_id(self, doc_id: int) -> ProcessedDocument | None:
        return self.db.query(ProcessedDocument).filter(ProcessedDocument.id == doc_id).first()

    def delete_by_id(self, doc_id: int) -> bool:
        doc = self.get_by_id(doc_id)
        if doc:
            self.db.delete(doc)
            self.db.commit()
            return True
        return False

    def delete_all(self) -> int:
        count = self.db.query(ProcessedDocument).delete()
        self.db.commit()
        return count
