# Document Intelligence Platform

![Python Badge](https://img.shields.io/badge/Python-3.10+-blue.svg)
![FastAPI Badge](https://img.shields.io/badge/FastAPI-0.115+-green.svg)
![Gemini AI Badge](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg)

AI-powered financial document extraction, validation & API platform.

## Solution Overview
This platform automates the extraction and validation of financial data from various document types (Invoices, Balance Sheets, Profit & Loss Statements, and Cash Flow Statements). It provides a robust backend API and a built-in dashboard for tracking processed documents.

## Architecture
The standard processing flow is as follows:
`Upload -> Validate -> OCR/Extract -> AI Extraction -> Financial Validation -> Store -> API/Dashboard`

Architecture diagrams can be found in the `docs/` folder (if available).

## Technology Stack

| Component | Technology |
|---|---|
| Backend | FastAPI (Python 3.10+) |
| Database | SQLite + SQLAlchemy |
| OCR | PyMuPDF (native PDF text) |
| AI Extraction | Google Gemini API (gemini-2.0-flash) |
| Frontend | HTML/CSS/JavaScript + Jinja2 |
| Deployment | Render / Railway / Koyeb |

## Local Setup

1. **Clone the repository**
2. **Create virtual environment:** `python -m venv venv`
3. **Activate:** 
   - Windows: `venv\Scripts\activate`
   - Linux/Mac: `source venv/bin/activate`
4. **Install dependencies:** `pip install -r requirements.txt`
5. **Environment Configuration:** Copy `.env.example` to `.env` and add your Gemini API key.
6. **Run Server:** `cd backend && uvicorn app.main:app --reload --port 8000`
7. **Access App:** Open [http://localhost:8000](http://localhost:8000)

## Environment Variables
Refer to `.env.example` for the required configuration parameters.

## API Documentation
Once the server is running, the Swagger UI is available at: [http://localhost:8000/docs](http://localhost:8000/docs)

### Endpoints
- `GET /api/v1/health` - Health check
- `POST /api/v1/documents/process` - Process a document
- `GET /api/v1/documents/{name}` - Get result by document name
- `GET /api/v1/documents` - List all processed documents

### API Examples

#### Upload Document
```bash
curl -X POST http://localhost:8000/api/v1/documents/process -F 'file=@invoice.pdf' -F 'document_type=invoice'
```

#### Get Document by Name
```bash
curl http://localhost:8000/api/v1/documents/invoice.pdf
```

## Supported Document Types
- Invoice
- Balance Sheet
- Profit & Loss
- Cash Flow Statement

## OCR & AI Model
- **PyMuPDF**: For native PDF text extraction.
- **Google Gemini (Flash series - gemini-3.6-flash / 3.8 / 3.5 / 2.5)**: For AI-powered field extraction (multimodal - accepts images with automatic fallback and retry mechanisms).

## Financial Validation Rules
The platform applies specific financial validation checks depending on the document type:
- **Invoice**: Validates that `Subtotal + Tax - Discount == Total` and `Sum of Line Items == Subtotal`.
- **Balance Sheet**: Validates the accounting equation `Total Assets == Total Liabilities + Equity`.
- **Profit & Loss**: Validates that `Gross Profit - Expenses == Net Income` (or similar standard structures).
- **Cash Flow**: Validates standard cash flow operations metrics.

## Database
Uses a local SQLite database storing processed documents with all extraction and validation results.

## Known Limitations
- Free tier Gemini API rate limits
- SQLite single-writer limitation
- No document classification (type must be specified)
- No authentication/authorization

## Production Improvements
- PostgreSQL for concurrent access
- Redis for caching
- Celery/background workers for async processing
- Authentication & RBAC
- Document versioning & audit trail
- Monitoring & alerting
- Horizontal scaling

## AI Tools Used
This project was developed with the assistance of AI agents to accelerate scaffolding, boilerplate generation, and testing configurations.
