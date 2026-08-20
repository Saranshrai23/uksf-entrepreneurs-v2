from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
UPLOAD_DIR = APP_DIR / "uploads"
PHOTO_DIR = UPLOAD_DIR / "photos"
LOGO_DIR = UPLOAD_DIR / "logos"
QR_DIR = APP_DIR / "generated_qr"
DATA_DIR = BASE_DIR / "data"

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'uksf.db'}")
SECRET_KEY = os.getenv("SECRET_KEY", "change-this-in-production")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
SESSION_HTTPS_ONLY = os.getenv("SESSION_HTTPS_ONLY", "false").lower() == "true"
MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)))
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}

for directory in (PHOTO_DIR, LOGO_DIR, QR_DIR):
    directory.mkdir(parents=True, exist_ok=True)
