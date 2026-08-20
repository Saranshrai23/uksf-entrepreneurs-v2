# Migration from static v1 to dynamic v2

## What stays from v1

- The 32 entrepreneur seed records in `data/entrepreneurs.json`.
- The idea of one permanent slug per entrepreneur.
- Python-based QR generation.
- The standard public profile fields and placeholder behavior.

## What changes

| v1 | v2 |
|---|---|
| JSON is the live data source | Database is the live data source; JSON is seed/import data |
| Python generates static HTML | FastAPI renders the same reusable template dynamically |
| GitHub Pages can host the site | Dynamic Python hosting + PostgreSQL are required |
| No login | Register/login/session authentication |
| No profile ownership | `owner_id` limits each user to their own profile |
| New people require code changes | New user creates profile from web form |
| No approval | New profile must be approved by admin |
| Photos/logos copied manually | Owner uploads photo/logo from the form |

## Recommended Git workflow

Keep the current v1 implementation intact until the mentor reviews v2.

```bash
git checkout -b feature/dynamic-profile-v2
```

Replace/add the v2 application on that branch, test it locally, then raise a PR into `main` after review.

## Deployment note

Do not configure v2 as a GitHub Pages site. GitHub Pages serves static content and cannot run the FastAPI application or PostgreSQL database.

Set the final deployed HTTPS URL in `BASE_URL`, then run:

```bash
python scripts/regenerate_qr.py
```

This ensures every QR contains the final dynamic application's public profile URL.
