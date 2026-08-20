import io
import os

import qrcode

from app.services.storage import upload_bytes, get_file_url


APP_BASE_URL = os.environ["APP_BASE_URL"].rstrip("/")


def generate_profile_qr(profile_id):
    profile_url = f"{APP_BASE_URL}/profile/{profile_id}"

    qr = qrcode.make(profile_url)

    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")

    key = f"qr/{profile_id}.png"

    upload_bytes(
        buffer.getvalue(),
        key,
        "image/png"
    )

    return {
        "profile_url": profile_url,
        "qr_key": key,
        "qr_url": get_file_url(key)
    }
