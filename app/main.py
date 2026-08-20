import json
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from .config import APP_DIR, BASE_URL, QR_DIR, SECRET_KEY, SESSION_HTTPS_ONLY, UPLOAD_DIR
from .db import Base, engine, get_db
from .models import Profile, User
from .security import (
    ensure_csrf,
    hash_password,
    normalize_email,
    require_login,
    validate_email,
    verify_csrf,
    verify_password,
)
from .services import (
    generate_qr,
    normalize_optional_url,
    profile_services,
    save_image,
    services_to_list,
    unique_slug,
)

app = FastAPI(title="Entrepreneur Digital Profiles", version="2.0.0")
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    https_only=SESSION_HTTPS_ONLY,
    same_site="lax",
    max_age=60 * 60 * 12,
)

app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/qr", StaticFiles(directory=QR_DIR), name="qr")
templates = Jinja2Templates(directory=APP_DIR / "templates")
templates.env.globals["profile_services"] = profile_services
templates.env.globals["base_url"] = BASE_URL


@app.on_event("startup")
def startup() -> None:
    Base.metadata.create_all(bind=engine)


def db_user(db: Session, request: Request) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, int(user_id))


def flash(request: Request, message: str, kind: str = "info") -> None:
    request.session["flash"] = {"message": message, "kind": kind}


def template_context(request: Request, db: Session, **extra):
    context = {
        "request": request,
        "current_user": db_user(db, request),
        "csrf_token": ensure_csrf(request),
        "flash": request.session.pop("flash", None),
    }
    context.update(extra)
    return context


def redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url=url, status_code=status.HTTP_303_SEE_OTHER)


def require_admin(db: Session, request: Request) -> User:
    user_id = require_login(request)
    user = db.get(User, user_id)
    if not user or not user.is_active or user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def require_active_user(db: Session, request: Request) -> User:
    user_id = require_login(request)
    user = db.get(User, user_id)
    if not user or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=401, detail="Active login required")
    return user


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/", response_class=HTMLResponse)
def home(request: Request, q: str = "", db: Session = Depends(get_db)):
    stmt = select(Profile).where(Profile.status == "published").order_by(Profile.name)
    if q.strip():
        term = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                Profile.name.ilike(term),
                Profile.company.ilike(term),
                Profile.designation.ilike(term),
                Profile.location.ilike(term),
            )
        )
    profiles = list(db.scalars(stmt).all())
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context=template_context(request, db, profiles=profiles, q=q),
    )


@app.get("/profiles/{slug}", response_class=HTMLResponse)
def public_profile(slug: str, request: Request, db: Session = Depends(get_db)):
    profile = db.scalar(select(Profile).where(Profile.slug == slug, Profile.status == "published"))
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    qr_path = QR_DIR / f"{profile.slug}.png"
    if not qr_path.exists():
        generate_qr(profile)
    return templates.TemplateResponse(
        request=request,
        name="public_profile.html",
        context=template_context(request, db, profile=profile),
    )


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    if db_user(db, request):
        return redirect("/dashboard")
    return templates.TemplateResponse(
        request=request,
        name="register.html",
        context=template_context(request, db),
    )


@app.post("/register")
def register(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    email = normalize_email(email)
    if not validate_email(email):
        flash(request, "Enter a valid email address.", "error")
        return redirect("/register")
    if len(password) < 10:
        flash(request, "Password must be at least 10 characters.", "error")
        return redirect("/register")
    if password != confirm_password:
        flash(request, "Passwords do not match.", "error")
        return redirect("/register")
    if db.scalar(select(User).where(User.email == email)):
        flash(request, "An account already exists for this email.", "error")
        return redirect("/login")

    user = User(email=email, password_hash=hash_password(password), role="user")
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session.clear()
    request.session["user_id"] = user.id
    ensure_csrf(request)
    flash(request, "Account created. You can now create a profile or ask the admin to assign an existing profile to you.", "success")
    return redirect("/dashboard")


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    if db_user(db, request):
        return redirect("/dashboard")
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context=template_context(request, db),
    )


@app.post("/login")
def login(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    csrf_token: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    email = normalize_email(email)
    user = db.scalar(select(User).where(User.email == email))
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        flash(request, "Invalid email or password.", "error")
        return redirect("/login")
    request.session.clear()
    request.session["user_id"] = user.id
    ensure_csrf(request)
    return redirect("/admin" if user.role == "admin" else "/dashboard")


@app.post("/logout")
def logout(request: Request, csrf_token: Annotated[str, Form()]):
    verify_csrf(request, csrf_token)
    request.session.clear()
    return redirect("/")


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_active_user(db, request)
    profile = db.scalar(select(Profile).where(Profile.owner_id == user.id))
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context=template_context(request, db, profile=profile),
    )


@app.get("/profile/new", response_class=HTMLResponse)
def new_profile_page(request: Request, db: Session = Depends(get_db)):
    user = require_active_user(db, request)
    if db.scalar(select(Profile).where(Profile.owner_id == user.id)):
        return redirect("/profile/edit")
    return templates.TemplateResponse(
        request=request,
        name="profile_form.html",
        context=template_context(request, db, profile=None, mode="create", services_text=""),
    )


async def apply_profile_form(
    profile: Profile,
    *,
    name: str,
    designation: str,
    company: str,
    location: str,
    email: str,
    about: str,
    category: str,
    services: str,
    website: str,
    linkedin: str,
    photo: UploadFile | None,
    logo: UploadFile | None,
):
    profile.name = name.strip()
    profile.designation = designation.strip()
    profile.company = company.strip()
    profile.location = location.strip()
    profile.email = email.strip()
    profile.about = about.strip()
    profile.category = category.strip()
    profile.services_json = json.dumps(services_to_list(services), ensure_ascii=False)
    profile.website = normalize_optional_url(website)
    profile.linkedin = normalize_optional_url(linkedin)
    profile.photo_filename = await save_image(photo, "photo", profile.photo_filename)
    profile.logo_filename = await save_image(logo, "logo", profile.logo_filename)


@app.post("/profile/new")
async def create_profile(
    request: Request,
    name: Annotated[str, Form()],
    designation: Annotated[str, Form()] = "",
    company: Annotated[str, Form()] = "",
    location: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    about: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    services: Annotated[str, Form()] = "",
    website: Annotated[str, Form()] = "",
    linkedin: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
    photo: UploadFile | None = File(default=None),
    logo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    user = require_active_user(db, request)
    if db.scalar(select(Profile).where(Profile.owner_id == user.id)):
        flash(request, "Your account already owns a profile.", "error")
        return redirect("/dashboard")
    if not name.strip():
        flash(request, "Name is required.", "error")
        return redirect("/profile/new")

    profile = Profile(owner_id=user.id, slug=unique_slug(db, name), name=name.strip(), status="pending")
    try:
        await apply_profile_form(
            profile,
            name=name, designation=designation, company=company, location=location,
            email=email, about=about, category=category, services=services,
            website=website, linkedin=linkedin, photo=photo, logo=logo,
        )
    except ValueError as exc:
        flash(request, str(exc), "error")
        return redirect("/profile/new")
    db.add(profile)
    db.commit()
    flash(request, "Profile submitted. It is pending admin approval before becoming public.", "success")
    return redirect("/dashboard")


@app.get("/profile/edit", response_class=HTMLResponse)
def edit_profile_page(request: Request, db: Session = Depends(get_db)):
    user = require_active_user(db, request)
    profile = db.scalar(select(Profile).where(Profile.owner_id == user.id))
    if not profile:
        return redirect("/profile/new")
    services_text = "\n".join(profile_services(profile))
    return templates.TemplateResponse(
        request=request,
        name="profile_form.html",
        context=template_context(request, db, profile=profile, mode="edit", services_text=services_text),
    )


@app.post("/profile/edit")
async def edit_profile(
    request: Request,
    name: Annotated[str, Form()],
    designation: Annotated[str, Form()] = "",
    company: Annotated[str, Form()] = "",
    location: Annotated[str, Form()] = "",
    email: Annotated[str, Form()] = "",
    about: Annotated[str, Form()] = "",
    category: Annotated[str, Form()] = "",
    services: Annotated[str, Form()] = "",
    website: Annotated[str, Form()] = "",
    linkedin: Annotated[str, Form()] = "",
    csrf_token: Annotated[str, Form()] = "",
    photo: UploadFile | None = File(default=None),
    logo: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    user = require_active_user(db, request)
    profile = db.scalar(select(Profile).where(Profile.owner_id == user.id))
    if not profile:
        return redirect("/profile/new")
    if not name.strip():
        flash(request, "Name is required.", "error")
        return redirect("/profile/edit")

    try:
        await apply_profile_form(
            profile,
            name=name, designation=designation, company=company, location=location,
            email=email, about=about, category=category, services=services,
            website=website, linkedin=linkedin, photo=photo, logo=logo,
        )
    except ValueError as exc:
        flash(request, str(exc), "error")
        return redirect("/profile/edit")

    # Keep an already published profile public on normal owner edits.
    # A rejected profile is resubmitted for admin review.
    if profile.status == "rejected":
        profile.status = "pending"
        profile.rejection_reason = ""
    db.commit()
    if profile.status == "published":
        generate_qr(profile)
    flash(request, "Profile updated successfully." if profile.status == "published" else "Profile saved and is awaiting admin approval.", "success")
    return redirect("/dashboard")


@app.get("/admin", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    require_admin(db, request)
    pending = list(db.scalars(select(Profile).where(Profile.status == "pending").order_by(Profile.created_at)).all())
    published = list(db.scalars(select(Profile).where(Profile.status == "published").order_by(Profile.name)).all())
    rejected = list(db.scalars(select(Profile).where(Profile.status == "rejected").order_by(Profile.updated_at.desc())).all())
    users = list(db.scalars(select(User).where(User.role == "user").order_by(User.email)).all())
    return templates.TemplateResponse(
        request=request,
        name="admin.html",
        context=template_context(request, db, pending=pending, published=published, rejected=rejected, users=users),
    )


@app.post("/admin/profiles/{profile_id}/approve")
def approve_profile(
    profile_id: int,
    request: Request,
    csrf_token: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    require_admin(db, request)
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.status = "published"
    profile.rejection_reason = ""
    db.commit()
    db.refresh(profile)
    generate_qr(profile)
    flash(request, f"{profile.name} approved and published.", "success")
    return redirect("/admin")


@app.post("/admin/profiles/{profile_id}/reject")
def reject_profile(
    profile_id: int,
    request: Request,
    csrf_token: Annotated[str, Form()],
    reason: Annotated[str, Form()] = "",
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    require_admin(db, request)
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile.status = "rejected"
    profile.rejection_reason = reason.strip()
    db.commit()
    flash(request, f"{profile.name} rejected.", "info")
    return redirect("/admin")


@app.post("/admin/profiles/{profile_id}/assign")
def assign_profile_owner(
    profile_id: int,
    request: Request,
    csrf_token: Annotated[str, Form()],
    owner_email: Annotated[str, Form()],
    db: Session = Depends(get_db),
):
    verify_csrf(request, csrf_token)
    require_admin(db, request)
    profile = db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    email = normalize_email(owner_email)
    user = db.scalar(select(User).where(User.email == email, User.role == "user"))
    if not user:
        flash(request, "No registered user found for that email.", "error")
        return redirect("/admin")
    other = db.scalar(select(Profile).where(Profile.owner_id == user.id, Profile.id != profile.id))
    if other:
        flash(request, "That user already owns another profile.", "error")
        return redirect("/admin")
    profile.owner_id = user.id
    db.commit()
    flash(request, f"{profile.name} is now assigned to {user.email}.", "success")
    return redirect("/admin")
