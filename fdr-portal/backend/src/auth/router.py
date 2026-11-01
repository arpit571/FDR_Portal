"""Auth router — login and /me endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import User
from src.auth.auth import verify_password, create_access_token, get_current_user, get_user_roles
from src.audit.audit import write_audit

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower().strip()).first()
    if not user or not verify_password(body.password, user.password_hash):
        # Audit failed attempt
        write_audit(db, user_id=None, entity_type="auth", entity_id=body.email,
                    action="LOGIN_FAILED", ip=request.client.host if request.client else None)
        db.commit()
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    roles = get_user_roles(user)
    token = create_access_token({"sub": user.id, "roles": roles})

    write_audit(db, user_id=user.id, entity_type="auth", entity_id=user.id,
                action="LOGIN_SUCCESS", ip=request.client.host if request.client else None)
    db.commit()

    return {"data": {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "roles": roles,
            "institution_id": user.institution_id,
        }
    }}


@router.get("/me")
def me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    roles = get_user_roles(current_user)
    return {"data": {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "roles": roles,
        "institution_id": current_user.institution_id,
    }}
