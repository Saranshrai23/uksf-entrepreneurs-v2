import argparse
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.models import User
from app.security import hash_password, normalize_email, validate_email


def main():
    parser = argparse.ArgumentParser(description="Create or promote an admin user")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args()

    email = normalize_email(args.email)
    if not validate_email(email):
        raise SystemExit("Invalid email")
    if len(args.password) < 10:
        raise SystemExit("Password must be at least 10 characters")

    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user:
            user.role = "admin"
            user.password_hash = hash_password(args.password)
            user.is_active = True
            action = "Updated"
        else:
            user = User(email=email, password_hash=hash_password(args.password), role="admin")
            db.add(user)
            action = "Created"
        db.commit()
    print(f"{action} admin: {email}")


if __name__ == "__main__":
    main()
