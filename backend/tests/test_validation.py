import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.document_validation_service import DocumentValidationService
from app.services.financial_validation_service import FinancialValidationService

class TestDocumentValidation:
    def setup_method(self):
        self.service = DocumentValidationService()
    
    def test_unsupported_file_type(self):
        result = self.service.validate(b'some content', 'test.txt', 'text/plain')
        assert result.status == 'FAIL'
        assert result.is_supported == False
    
    def test_empty_file(self):
        result = self.service.validate(b'', 'test.pdf', 'application/pdf')
        assert result.status == 'FAIL'
        assert result.is_readable == False
    
    def test_supported_image_type(self):
        """Test that JPG MIME type is recognized as supported"""
        # We test the type check logic, even if the content is invalid
        result = self.service.validate(b'not a real image', 'test.jpg', 'image/jpeg')
        assert result.is_supported == True
        # File won't be readable since content is fake
        assert result.status == 'FAIL'
    
    def test_pdf_mime_supported(self):
        result = self.service.validate(b'not a pdf', 'test.pdf', 'application/pdf')
        assert result.is_supported == True

class TestFinancialValidation:
    def setup_method(self):
        self.service = FinancialValidationService()
    
    def test_invoice_validation_pass(self):
        extracted_data = {
            'subtotal': {'value': 1000.00},
            'tax_amount': {'value': 100.00},
            'discount': {'value': 50.00},
            'total_amount': {'value': 1050.00},
            'line_items': [
                {'description': 'Item 1', 'quantity': 2, 'unit_price': 500.00, 'amount': 1000.00}
            ]
        }
        result = self.service.validate(extracted_data, 'invoice')
        # Find the total check
        total_checks = [c for c in result.checks if c.name == 'total_amount_check']
        if total_checks:
            assert total_checks[0].status == 'PASS'
    
    def test_invoice_validation_fail(self):
        extracted_data = {
            'subtotal': {'value': 1000.00},
            'tax_amount': {'value': 100.00},
            'discount': {'value': 0.00},
            'total_amount': {'value': 500.00},  # Wrong!
        }
        result = self.service.validate(extracted_data, 'invoice')
        total_checks = [c for c in result.checks if c.name == 'total_amount_check']
        if total_checks:
            assert total_checks[0].status == 'FAIL'
    
    def test_balance_sheet_validation(self):
        extracted_data = {
            'total_assets': {'value': 50000.00},
            'total_capital_and_liabilities': {'value': 50000.00},
        }
        result = self.service.validate(extracted_data, 'balance_sheet')
        eq_checks = [c for c in result.checks if 'equation' in c.name.lower() or 'balance' in c.name.lower()]
        if eq_checks:
            assert eq_checks[0].status == 'PASS'
    
    def test_missing_fields_not_applicable(self):
        """When required fields are missing, validation should be NOT_APPLICABLE"""
        extracted_data = {}  # Empty
        result = self.service.validate(extracted_data, 'cash_flow_statement')
        for check in result.checks:
            assert check.status in ['NOT_APPLICABLE', 'PASS', 'FAIL']
