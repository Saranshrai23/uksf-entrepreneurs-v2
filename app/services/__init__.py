import json
import re
import uuid
from pathlib import Path
from urllib.parse import urlparse

import qrcode
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import ALLOWED_IMAGE_TYPES, BASE_URL, LOGO_DIR, MAX_UPLOAD_BYTES, PHOTO_DIR, QR_DIR
from ..models import Profile


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or "profile"


def unique_slug(db: Session, name: str, current_profile_id: int | None = None) -> str:
    base = slugify(name)
    candidate = base
    number = 2
    while True:
        stmt = select(Profile).where(Profile.slug == candidate)
        existing = db.scalar(stmt)
        if existing is None or existing.id == current_profile_id:
            return candidate
        candidate = f"{base}-{number}"
        number += 1


def services_to_list(raw: str) -> list[str]:
    return [line.strip() for line in raw.splitlines() if line.strip()]


def profile_services(profile: Profile) -> list[str]:
    try:
        data = json.loads(profile.services_json or "[]")
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def normalize_optional_url(value: str) -> str:
    value = value.strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must start with http:// or https://")
    return value


async def save_image(upload: UploadFile | None, kind: str, old_filename: str = "") -> str:
    if upload is None or not upload.filename:
        return old_filename
    ext = ALLOWED_IMAGE_TYPES.get(upload.content_type or "")
    if not ext:
        raise HTTPException(status_code=400, detail="Only JPG, PNG and WEBP images are allowed")
    content = await upload.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="Image is too large")
    directory: Path = PHOTO_DIR if kind == "photo" else LOGO_DIR
    filename = f"{uuid.uuid4().hex}{ext}"
    path = directory / filename
    path.write_bytes(content)
    if old_filename:
        old = directory / old_filename
        if old.exists() and old.is_file():
            old.unlink(missing_ok=True)
    return filename


def generate_qr(profile: Profile) -> Path:
    url = f"{BASE_URL}/profiles/{profile.slug}"
    output = QR_DIR / f"{profile.slug}.png"
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").save(output)
    return output
