from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import login_limiter, register_limiter
from app.core.security import DUMMY_PASSWORD_HASH, create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import User
from app.repositories import repository as repo
from app.routers.deps import get_current_user
from app.schemas.schemas import RegisterRequest, TokenResponse, UserOut
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, request: Request, db: Session = Depends(get_db)) -> User:
    register_limiter.check(_client_ip(request))
    if repo.get_user_by_email(db, data.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this e-mail already exists.")
    user = User(email=data.email, hashed_password=hash_password(data.password), full_name=data.full_name)
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="An account with this e-mail already exists."
        ) from None
    audit.record(db, "user.register", user_id=user.id, resource_type="user", resource_id=user.id, request=request)
    return user


@router.post("/token", response_model=TokenResponse)
def login(
    request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)
) -> TokenResponse:
    """OAuth2 password flow: `username` is the e-mail address."""
    email = form.username.strip().lower()
    login_limiter.check(f"{_client_ip(request)}:{email}")
    user = repo.get_user_by_email(db, email)
    # Always run bcrypt so response time does not reveal whether the account exists.
    valid = verify_password(form.password, user.hashed_password if user else DUMMY_PASSWORD_HASH)
    if user is None or not valid or not user.is_active:
        audit.record(db, "user.login_failed", user_id=user.id if user else None, request=request)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect e-mail or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    audit.record(db, "user.login", user_id=user.id, request=request)
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=get_settings().ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> User:
    return user
