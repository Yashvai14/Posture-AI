from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import InvalidTokenError, decode_access_token
from app.db.session import get_db
from app.models.models import User
from app.repositories import repository as repo

# Tokens are accepted only from the Authorization header, never from query strings or cookies.
bearer_scheme = HTTPBearer(auto_error=False)

CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated.",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise CREDENTIALS_ERROR
    try:
        user_id = decode_access_token(credentials.credentials)
    except InvalidTokenError:
        raise CREDENTIALS_ERROR from None
    user = repo.get_user(db, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user


def get_current_user_with_query_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = None,
    db: Session = Depends(get_db),
) -> User:
    raw_token = None
    if credentials is not None and credentials.scheme.lower() == "bearer":
        raw_token = credentials.credentials
    elif token:
        raw_token = token

    if not raw_token:
        raise CREDENTIALS_ERROR
    try:
        user_id = decode_access_token(raw_token)
    except InvalidTokenError:
        raise CREDENTIALS_ERROR from None
    user = repo.get_user(db, user_id)
    if user is None or not user.is_active:
        raise CREDENTIALS_ERROR
    return user

