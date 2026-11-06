import json
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as URLRequest, urlopen

from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import (
    Token,
    UserRegister,
    UserResponse,
    VerifyOTP,
    ForgotPasswordRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    RegistrationResponse,
)
from app.services.email_service import send_otp_email, generate_otp

router = APIRouter(prefix="/auth", tags=["Authentification"])
logger = logging.getLogger(__name__)
_google_states: dict[str, float] = {}
RATE_LIMIT = 5
RATE_WINDOW = timedelta(hours=1)


def _client_id(request: FastAPIRequest, email: str) -> tuple[str, str]:
    ip = request.client.host if request.client else "unknown"
    return f"email:{email.casefold()}", f"ip:{ip}"


def _rate_limited(db: Session, action: str, identifiers: tuple[str, str]) -> bool:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for identifier in identifiers:
        row = db.execute(
            text(
                "SELECT window_started, attempts FROM auth_rate_limits "
                "WHERE key = :key"
            ),
            {"key": f"{action}:{identifier}"},
        ).mappings().first()
        if row and now - row["window_started"] < RATE_WINDOW and row["attempts"] >= RATE_LIMIT:
            return True
    return False


def _record_failed_attempt(
    db: Session, action: str, identifiers: tuple[str, str]
) -> None:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for identifier in identifiers:
        key = f"{action}:{identifier}"
        row = db.execute(
            text(
                "SELECT window_started, attempts FROM auth_rate_limits "
                "WHERE key = :key FOR UPDATE"
            ),
            {"key": key},
        ).mappings().first()
        if not row or now - row["window_started"] >= RATE_WINDOW:
            db.execute(
                text(
                    """
                    INSERT INTO auth_rate_limits (key, window_started, attempts)
                    VALUES (:key, :started, 1)
                    ON CONFLICT (key) DO UPDATE SET
                        window_started = EXCLUDED.window_started,
                        attempts = 1
                    """
                ),
                {"key": key, "started": now},
            )
        else:
            db.execute(
                text(
                    "UPDATE auth_rate_limits SET attempts = attempts + 1 "
                    "WHERE key = :key"
                ),
                {"key": key},
            )
    db.commit()


def _clear_rate_limit(db: Session, action: str, identifiers: tuple[str, str]) -> None:
    db.execute(
        text("DELETE FROM auth_rate_limits WHERE key IN (:email_key, :ip_key)"),
        {
            "email_key": f"{action}:{identifiers[0]}",
            "ip_key": f"{action}:{identifiers[1]}",
        },
    )
    db.commit()


def _too_many_requests() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="too many requests, try later",
        headers={"Retry-After": "3600"},
    )


def _otp_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at < datetime.now(timezone.utc)


def _google_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID and settings.GOOGLE_CLIENT_SECRET)


@router.get("/google/login")
def google_login():
    if not _google_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to backend/.env.",
        )

    state = secrets.token_urlsafe(32)
    _google_states[state] = time.time() + 600
    params = urlencode(
        {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "state": state,
            "prompt": "select_account",
        }
    )
    return RedirectResponse(
        f"https://accounts.google.com/o/oauth2/v2/auth?{params}"
    )


def _google_post(url: str, data: dict[str, str]) -> dict:
    request = URLRequest(
        url,
        data=urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _google_get(url: str) -> dict:
    with urlopen(URLRequest(url), timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


@router.get("/google/callback")
def google_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/auth/callback?error=google_{error}"
        )
    if not code or not state or _google_states.pop(state, 0) < time.time():
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/auth/callback?error=invalid_google_state"
        )

    try:
        tokens = _google_post(
            "https://oauth2.googleapis.com/token",
            {
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        id_token = tokens.get("id_token")
        if not id_token:
            raise ValueError("Google did not return an ID token.")
        
        profile = _google_get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={id_token}"
        )
        if (
            profile.get("aud") != settings.GOOGLE_CLIENT_ID
            or profile.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
            or profile.get("email_verified") != "true"
            or not profile.get("email")
            or not profile.get("sub")
        ):
            raise ValueError("Google account verification failed.")
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError):
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/auth/callback?error=google_auth_failed"
        )

    google_email = profile["email"].strip().casefold()
    try:
        user = db.query(User).filter(User.google_sub == profile["sub"]).first()
        if not user:
            user = (
                db.query(User)
                .filter(func.lower(User.email) == google_email)
                .first()
            )
        if user:
            if not user.google_sub:
                user.google_sub = profile["sub"]
            user.is_verified = True
        else:
            user = User(
                email=google_email,
                google_sub=profile["sub"],
                is_verified=True,
            )
            db.add(user)
        db.commit()
        db.refresh(user)
    except SQLAlchemyError:
        db.rollback()
        logger.exception("Google OAuth user persistence failed")
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/auth/callback?error=google_account_error"
        )

    access_token = create_access_token(data=user.id)
    frontend_url = getattr(
        settings, "FRONTEND_URL", "https://ali-pdf-agent.netlify.app"
    )

    return RedirectResponse(
        url=f"{frontend_url}/auth/callback#token={access_token}"
    )


@router.post(
    "/register",
    response_model=RegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(user_in: UserRegister, db: Session = Depends(get_db)):
    existing_user = (
        db.query(User).filter(User.email == user_in.email).first()
    )
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account already exists with this email address.",
        )

    otp = generate_otp()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)

    if not existing_user:
        new_user = User(
            email=user_in.email, 
            hashed_password=hash_password(user_in.password),
            is_verified=False,
            verification_code=otp,
            otp_expires_at=expires_at
        )
        db.add(new_user)
    else:
        existing_user.hashed_password = hash_password(user_in.password)
        existing_user.verification_code = otp
        existing_user.otp_expires_at = expires_at
        
    db.commit()

    send_otp_email(to_email=user_in.email, otp_code=otp, purpose="verification")
    return {
        "message": "Verification code sent by email. Please verify your account."
    }



@router.post("/verify-email", response_model=Token)
def verify_email(
    data: VerifyOTP,
    request: FastAPIRequest,
    db: Session = Depends(get_db),
):
    identifiers = _client_id(request, data.email)
    if _rate_limited(db, "verify-email", identifiers):
        raise _too_many_requests()
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        _record_failed_attempt(db, "verify-email", identifiers)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user or user.verification_code != data.code:
        _record_failed_attempt(db, "verify-email", identifiers)
        raise HTTPException(
            status_code=400, detail="Invalid verification code."
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified.",
        )

    if _otp_expired(user.otp_expires_at):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired.",
        )

    user.is_verified = True
    user.verification_code = None
    user.otp_expires_at = None
    db.commit()
    _clear_rate_limit(db, "verify-email", identifiers)

    access_token = create_access_token(data=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/resend-verification")
def resend_verification(
    data: ResendVerificationRequest, db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(status_code=404, detail="Account not found.")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email is already verified.")

    otp = generate_otp()
    user.verification_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
    db.commit()
    send_otp_email(to_email=data.email, otp_code=otp, purpose="verification")
    return {"message": "A new verification code has been sent."}

@router.post("/forgot-password")
def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        return "if an account with this email exists, a reset code has been sent."

    otp = generate_otp()
    user.reset_password_code = otp
    user.otp_expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)
    db.commit()

    send_otp_email(to_email=data.email, otp_code=otp, purpose="reset")
    return "if an account with this email exists, a reset code has been sent."

@router.post("/reset-password", response_model=Token)
def reset_password(
    data: ResetPasswordRequest,
    request: FastAPIRequest,
    db: Session = Depends(get_db),
):
    identifiers = _client_id(request, data.email)
    if _rate_limited(db, "reset-password", identifiers):
        raise _too_many_requests()
    user = db.query(User).filter(User.email == data.email).first()
    if not user or user.reset_password_code != data.code:
        _record_failed_attempt(db, "reset-password", identifiers)
        raise HTTPException(
            status_code=400, detail="Invalid Reset Code."
        )

    if _otp_expired(user.otp_expires_at):
        raise HTTPException(
            status_code=400, detail="Reset code has expired."
        )

    user.hashed_password = hash_password(data.new_password)
    user.reset_password_code = None
    user.otp_expires_at = None
    db.commit()
    _clear_rate_limit(db, "reset-password", identifiers)

    access_token = create_access_token(data=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(
    request: FastAPIRequest,
    login_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    identifiers = _client_id(request, login_data.username)
    if _rate_limited(db, "login", identifiers):
        raise _too_many_requests()
    user = db.query(User).filter(User.email == login_data.username).first()

    if not user or not verify_password(
        login_data.password, user.hashed_password
    ):
        _record_failed_attempt(db, "login", identifiers)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data=user.id)
    _clear_rate_limit(db, "login", identifiers)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Route secured : return the data of the connected user."""
    return current_user