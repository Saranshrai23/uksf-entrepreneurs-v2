import json
from pathlib import Path
from sqlalchemy import select

from app.config import DATA_DIR
from app.db import Base, SessionLocal, engine
from app.models import Profile
from app.services import generate_qr


def main():
    source = DATA_DIR / "entrepreneurs.json"
    if not source.exists():
        raise SystemExit(f"Missing seed file: {source}")
    records = json.loads(source.read_text(encoding="utf-8"))

    Base.metadata.create_all(bind=engine)
    added = 0
    with SessionLocal() as db:
        for item in records:
            slug = item.get("slug", "").strip()
            if not slug or db.scalar(select(Profile).where(Profile.slug == slug)):
                continue
            profile = Profile(
                owner_id=None,
                slug=slug,
                name=item.get("name", "").strip(),
                designation=item.get("designation", "").strip(),
                company=item.get("company", "").strip(),
                location=item.get("location", "").strip(),
                email=item.get("email", "").strip(),
                about=item.get("about", "").strip(),
                category=item.get("category", "").strip(),
                services_json=json.dumps(item.get("services", []), ensure_ascii=False),
                website=item.get("website", "").strip(),
                linkedin=item.get("linkedin", "").strip(),
                status="published",
                source_url=item.get("source_url", "").strip(),
            )
            db.add(profile)
            db.flush()
            added += 1
        db.commit()

        profiles = list(db.scalars(select(Profile).where(Profile.status == "published")).all())
        for profile in profiles:
            generate_qr(profile)

    print(f"Seed complete. Added {added} profile(s). Published profiles: {len(profiles)}")


if __name__ == "__main__":
    main()
