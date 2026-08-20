# Entrepreneur Digital Profile & QR System — v2

This is the dynamic v2 implementation of the entrepreneur profile project.

The original GitHub Pages version proved the static **QR → profile** flow. This version adds the two approved requirements:

1. An existing profile owner can log in and edit their own profile through the webpage.
2. A new member can register, create a profile using the same template, and submit it for **admin approval** before publication.

## Core flow

### Existing entrepreneur

1. Register an account.
2. Admin verifies identity and assigns the existing imported profile to that registered email.
3. User logs in → Dashboard → Edit My Profile.
4. The public slug/URL remains unchanged, so the QR remains valid.

### New entrepreneur

1. Register → Login.
2. Create Profile using the common template.
3. Upload person photo and business logo.
4. Submit → status becomes `pending`.
5. Admin approves → status becomes `published`.
6. Python `qrcode` generates the permanent QR for `/profiles/<slug>`.

## Security model

- Passwords are scrypt-hashed; plain passwords are never stored.
- Signed session cookies are used for authentication.
- Forms use a session-backed CSRF token.
- A normal user can only edit a profile whose `owner_id` matches their account.
- Existing imported profiles are assigned only by an admin; users cannot self-claim arbitrary profiles.
- Uploaded images are limited to JPG, PNG and WEBP and 5 MB by default.
- New profiles require admin approval before they are public.

> MVP policy: once a profile is published, normal owner edits update it directly. A rejected profile returns to `pending` when corrected. If the business later requires approval for every edit, implement profile revisions so the last approved version stays public while changes wait for review.

## Stack

- Python 3.12
- FastAPI
- SQLAlchemy
- PostgreSQL for deployment; SQLite fallback for local development
- Jinja2 + HTML/CSS
- Python `qrcode`
- Local persistent upload volume for MVP; object storage can replace it later

## Run locally (quickest: SQLite)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt

export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export BASE_URL="http://localhost:8000"

python scripts/seed_profiles.py
python scripts/create_admin.py --email admin@example.com --password 'ChangeThis123!'
uvicorn app.main:app --reload
```

Open:

- Public directory: `http://localhost:8000/`
- Register: `http://localhost:8000/register`
- Login: `http://localhost:8000/login`
- Admin: `http://localhost:8000/admin`

## Run with PostgreSQL using Docker Compose

```bash
docker compose up -d --build
```

Seed the 32 current profiles and create an admin inside the app container:

```bash
docker compose exec app python scripts/seed_profiles.py
docker compose exec app python scripts/create_admin.py \
  --email admin@example.com \
  --password 'ChangeThis123!'
```

Then open `http://localhost:8000`.

## Existing-profile ownership

The 32 imported profiles are seeded as `published` and initially have no owner.

Secure workflow:

1. The actual profile owner registers an account.
2. Admin verifies the person's identity outside the application.
3. Admin opens `/admin` and assigns that published profile to the registered email.
4. The user can now edit only that profile.

This prevents anyone from claiming another person's public profile just because they know the person's public email address.

## Profile statuses

- `pending` — submitted by a new user and waiting for admin approval.
- `published` — public and QR-enabled.
- `rejected` — not public; user can correct it and resubmit.

## QR behavior

QR code generation is Python-based. On approval, the app generates:

`app/generated_qr/<slug>.png`

The QR contains:

`<BASE_URL>/profiles/<slug>`

Editing profile information does **not** change the QR because the slug remains fixed.

## Important production notes

GitHub Pages cannot run this dynamic backend. Keep the old repository/site as a POC if needed, but deploy v2 on a service that runs Python and PostgreSQL (for example your company infrastructure, a VM/container platform, or another approved hosting platform).

Before production:

- Use PostgreSQL, not SQLite.
- Set a strong `SECRET_KEY` in secret management.
- Set `BASE_URL` to the real HTTPS application URL.
- Set `SESSION_HTTPS_ONLY=true` behind HTTPS.
- Put uploads in persistent object storage or a persistent volume.
- Add database migrations (Alembic) before schema changes are managed in production.
- Add email verification/password reset if the application is exposed beyond an internal controlled user group.

## Test

```bash
pytest -q
```

## Proposed repository migration

Do not overwrite the v1 history without review. Recommended:

```bash
git checkout -b feature/dynamic-profile-v2
# copy this v2 project into the repo
# review locally
# commit and raise a PR
```

That lets the mentor compare the original POC with the new architecture before merging.

## If the final domain changes

Set `BASE_URL` to the final HTTPS domain and regenerate all published QR images:

```bash
export BASE_URL="https://profiles.example.com"
python scripts/regenerate_qr.py
```

Do this **before mass printing QR codes**.
