import pytest
from fastapi.testclient import TestClient
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.core.database import init_db, Base, engine
from app.main import app

# Initialize DB tables before tests on a separate test database
@pytest.fixture(autouse=True, scope="module")
def setup_db():
    init_db()
    yield

client = TestClient(app)

def test_health_check():
    response = client.get('/api/v1/health')
    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'healthy'
    assert 'timestamp' in data

def test_list_documents_empty():
    response = client.get('/api/v1/documents')
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_upload_unsupported_file():
    """Test uploading an unsupported file type (.txt)"""
    response = client.post(
        '/api/v1/documents/process',
        data={'document_type': 'invoice'},
        files={'file': ('test.txt', b'This is a text file', 'text/plain')}
    )
    # Should return 200 with FAILED status (validation catches it)
    assert response.status_code == 200
    data = response.json()
    assert data['processing_status'] == 'FAILED'
    assert data['file_validation']['is_supported'] == False

def test_upload_invalid_document_type():
    """Test uploading with invalid document type"""
    response = client.post(
        '/api/v1/documents/process',
        data={'document_type': 'invalid_type'},
        files={'file': ('test.pdf', b'%PDF-1.4 fake', 'application/pdf')}
    )
    assert response.status_code in [400, 422]

def test_get_nonexistent_document():
    """Test GET for a document that doesn't exist"""
    response = client.get('/api/v1/documents/nonexistent_file.pdf')
    assert response.status_code == 404

def test_dashboard_page():
    """Test that the dashboard page loads (may return JSON fallback in test context)"""
    response = client.get('/')
    assert response.status_code == 200
