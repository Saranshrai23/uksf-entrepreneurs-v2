from sqlalchemy import select
from app.db import Base, SessionLocal, engine
from app.models import Profile
from app.services import generate_qr


def main():
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        profiles = list(db.scalars(select(Profile).where(Profile.status == "published")).all())
        for profile in profiles:
            generate_qr(profile)
    print(f"Regenerated {len(profiles)} QR code(s).")


if __name__ == "__main__":
    main()
