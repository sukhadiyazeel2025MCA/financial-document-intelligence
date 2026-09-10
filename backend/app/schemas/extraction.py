from pydantic import BaseModel, ConfigDict
from typing import Any, Optional

class ExtractedField(BaseModel):
    value: Any
    confidence: Optional[float] = None
    page_number: Optional[int] = None
    source_text: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None
    additional_fields: dict = {}

    model_config = ConfigDict(from_attributes=True)

class FinancialLineItem(BaseModel):
    label: str
    values: dict
    page_number: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)
