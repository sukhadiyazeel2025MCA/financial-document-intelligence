from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from datetime import datetime
from app.core.database import Base

class ProcessedDocument(Base):
    __tablename__ = 'processed_documents'

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_name = Column(String(255), nullable=False, index=True)
    document_type = Column(String(50), nullable=False)
    processing_status = Column(String(20), nullable=False)
    file_validation = Column(Text)
    extracted_data = Column(Text)
    validation_result = Column(Text)
    processing_metadata = Column(Text)
    overall_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
