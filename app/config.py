import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# On Vercel serverless functions, the root filesystem is read-only, so SQLite must live in /tmp
if os.getenv("VERCEL"):
    DEFAULT_DB = "sqlite:////tmp/filmlog.db"
else:
    DEFAULT_DB = "sqlite:///./filmlog.db"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)
JWT_SECRET = os.getenv("JWT_SECRET", "super_secret_filmlog_jwt_key_gdgoc_2026")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
