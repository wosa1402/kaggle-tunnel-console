import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE_DIR / "data")).resolve()
CREDS_DIR = DATA_DIR / "creds"
WORK_DIR = DATA_DIR / "work"
DB_PATH = DATA_DIR / "app.db"
TEMPLATE_IPYNB = Path(os.getenv("TEMPLATE_IPYNB", DATA_DIR / "template.ipynb")).resolve()

DATA_DIR.mkdir(parents=True, exist_ok=True)
CREDS_DIR.mkdir(parents=True, exist_ok=True)
WORK_DIR.mkdir(parents=True, exist_ok=True)

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "change_me_please")

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "168"))

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "").strip()

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))

FRONTEND_DIR = BASE_DIR / "frontend"
