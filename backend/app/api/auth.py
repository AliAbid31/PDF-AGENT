import datetime
import json
import secrets
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.user import Token, UserRegister, UserResponse, UserLogin, VerifyOTP, ForgotPasswordRequest, ResetPasswordRequest
from app.services.email_service import send_otp_email, generate_otp

router = APIRouter(prefix="/auth", tags=["Authentification"])
_google_states: dict[str, float] = {}


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
    request = Request(
        url,
        data=urlencode(data).encode("utf-8"),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def _google_get(url: str) -> dict:
    with urlopen(Request(url), timeout=15) as response:
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
    except (HTTPError, URLError, TimeoutError, ValueError, KeyError) as exc:
        return RedirectResponse(
            f"{settings.FRONTEND_URL}/auth/callback?error=google_auth_failed"
        )

    user = db.query(User).filter(User.google_sub == profile["sub"]).first()
    if not user:
        user = db.query(User).filter(User.email == profile["email"]).first()
    if user:
        if not user.google_sub:
            user.google_sub = profile["sub"]
    else:
        user = User(email=profile["email"], google_sub=profile["sub"])
        db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(data=user.id)
    return RedirectResponse(
        f"{settings.FRONTEND_URL}/auth/callback#token={access_token}"
    )


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
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
    expires_at = datetime.now(time.timezone.utc) + time.timedelta(minutes=30)

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
def verify_email(data: VerifyOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if not user or user.verification_code != data.code:
        raise HTTPException(
            status_code=400, detail="Invalid verification code."
        )

    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified.",
        )

    if user.otp_expires_at < datetime.now(time.timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired.",
        )

    user.is_verified = True
    user.verification_code = None
    user.otp_expires_at = None
    db.commit()

    access_token = create_access_token(data=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

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
def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or user.reset_password_code != data.code:
        raise HTTPException(
            status_code=400, detail="Invalid Reset Code."
        )

    if user.otp_expires_at < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=400, detail="Reset code has expired."
        )

    user.hashed_password = hash_password(data.new_password)
    user.reset_password_code = None
    user.otp_expires_at = None
    db.commit()

    access_token = create_access_token(data=user.id)
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
def login(
    login_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == login_data.username).first()

    if not user or not verify_password(
        login_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password incorrect.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data=user.id)

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Route secured : return the data of the connected user."""
    return current_user