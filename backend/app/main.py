import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.documents import router
from app.core.database import init_db
from app.core.logging_config import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    os.makedirs('uploads', exist_ok=True)
    yield

app = FastAPI(
    title='Document Intelligence API',
    description='AI-powered document extraction and validation platform',
    version='1.0.0',
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*']
)

from pathlib import Path
BACKEND_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BACKEND_DIR.parent
frontend_dir = ROOT_DIR / "frontend"
static_dir = frontend_dir / "static"
templates_dir = frontend_dir / "templates"

if static_dir.exists():
    app.mount('/static', StaticFiles(directory=str(static_dir)), name='static')
    
templates = None
if templates_dir.exists():
    templates = Jinja2Templates(directory=str(templates_dir))

app.include_router(router)

@app.get('/', include_in_schema=False)
async def dashboard(request: Request):
    if templates:
        return templates.TemplateResponse('index.html', {'request': request})
    return {"message": "Frontend templates not found"}

@app.get('/result/{document_id}', include_in_schema=False)
async def view_result(request: Request, document_id: int):
    if templates:
        return templates.TemplateResponse('result.html', {'request': request, 'document_id': document_id})
    return {"message": "Frontend templates not found"}

@app.get('/result/name/{document_name}', include_in_schema=False)
async def view_result_by_name(request: Request, document_name: str):
    if templates:
        return templates.TemplateResponse('result.html', {'request': request, 'document_name': document_name})
    return {"message": "Frontend templates not found"}
