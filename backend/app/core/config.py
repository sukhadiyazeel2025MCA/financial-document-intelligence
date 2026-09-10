import os
from pathlib import Path
from pydantic_settings import BaseSettings

# Locate directories
APP_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = APP_DIR.parent
ROOT_DIR = BACKEND_DIR.parent

env_path = ROOT_DIR / ".env" if (ROOT_DIR / ".env").exists() else (BACKEND_DIR / ".env" if (BACKEND_DIR / ".env").exists() else ".env")
db_path = str((ROOT_DIR / "document_intelligence.db").resolve())

class Settings(BaseSettings):
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    DATABASE_URL: str = f"sqlite:///{db_path}"
    UPLOAD_DIR: str = str((ROOT_DIR / "uploads").resolve())
    MAX_FILE_SIZE_MB: int = 10
    MAX_PAGES: int = 3
    ALLOWED_EXTENSIONS: list[str] = ['.pdf', '.jpg', '.jpeg', '.png']
    ALLOWED_MIME_TYPES: list[str] = ['application/pdf', 'image/jpeg', 'image/png']
    FINANCIAL_TOLERANCE: float = 0.01
    LOG_LEVEL: str = 'INFO'

    model_config = {
        'env_file': str(env_path),
        'env_file_encoding': 'utf-8',
        'extra': 'ignore'
    }

try:
    settings = Settings()
except Exception:
    settings = Settings(_env_file=None)

