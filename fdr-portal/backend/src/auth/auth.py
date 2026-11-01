"""
Authentication — JWT creation/verification, bcrypt password hashing, RBAC middleware.
"""
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
import bcrypt
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import User, UserRole, Role
from src.config.settings import get_settings

settings = get_settings()
bearer_scheme = HTTPBearer(auto_error=False)

# Role constants
SUPER_ADMIN = "SUPER_ADMIN"
FINANCE_OFFICER = "FINANCE_OFFICER"
REVIEWER = "REVIEWER"
AICTE_OFFICER = "AICTE_OFFICER"
AUDITOR = "AUDITOR"


# ---------------------------------------------------------------------------
# Password helpers
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        pwd_bytes = plain.encode("utf-8")[:72]
        hashed_bytes = hashed.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hashed_bytes)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT helpers
# ---------------------------------------------------------------------------

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS))
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ---------------------------------------------------------------------------
# Current user dependency
# ---------------------------------------------------------------------------

def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    user_id: str = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    user = db.query(User).filter(User.id == user_id, User.active == True).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def get_user_roles(user: User) -> List[str]:
    return [ur.role.name for ur in user.roles]


def has_role(user: User, *roles: str) -> bool:
    user_roles = get_user_roles(user)
    return any(r in user_roles for r in roles)


# ---------------------------------------------------------------------------
# Role-based dependency factories
# ---------------------------------------------------------------------------

def require_roles(*roles: str):
    """Returns a FastAPI dependency that checks the user has one of the given roles."""
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if not has_role(current_user, *roles):
            raise HTTPException(
                status_code=403,
                detail=f"Requires one of roles: {list(roles)}"
            )
        return current_user
    return checker


def require_institution_scope(user: User, institution_id: str):
    """Raise 403 if a non-admin user tries to access another institution's data."""
    if has_role(user, SUPER_ADMIN, AICTE_OFFICER, AUDITOR):
        return  # these roles see all institutions
    if user.institution_id != institution_id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this institution's data"
        )
