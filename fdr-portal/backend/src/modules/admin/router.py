"""Admin router — demo clock, scheduler trigger, user management."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from src.config.database import get_db
from src.config.models import SystemSetting, User, UserRole, Role
from src.auth.auth import (get_current_user, require_roles, has_role, hash_password,
                           SUPER_ADMIN, AUDITOR)
from src.audit.audit import write_audit
from src.config.settings import get_settings

router = APIRouter()


class DemoClockBody(BaseModel):
    advance_days: Optional[int] = None
    set_date: Optional[str] = None  # ISO date string


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    roles: List[str]
    institution_id: Optional[str] = None
    active: bool = True


@router.post("/demo-clock", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def set_demo_clock(body: DemoClockBody, db: Session = Depends(get_db),
                   current_user=Depends(get_current_user)):
    from src.config.dates import today as get_today
    from datetime import date

    if body.set_date:
        new_date = body.set_date
    elif body.advance_days is not None:
        current = get_today()
        new_date = str(current + timedelta(days=body.advance_days))
    else:
        raise HTTPException(status_code=422, detail="Provide advance_days or set_date")

    # Store in system_settings
    setting = db.query(SystemSetting).filter(SystemSetting.key == "DEMO_DATE").first()
    if not setting:
        setting = SystemSetting(key="DEMO_DATE", value=new_date)
        db.add(setting)
    else:
        setting.value = new_date

    # Also update the in-process setting
    import os
    os.environ["DEMO_DATE"] = new_date
    from src.config.settings import get_settings as gs
    gs.cache_clear()

    write_audit(db, user_id=current_user.id, entity_type="system", entity_id="DEMO_DATE",
                action="SET_DEMO_CLOCK", after={"demo_date": new_date})
    db.commit()

    # Re-run scheduler jobs immediately after clock advance
    from src.jobs.scheduler import run_alert_job, run_escalation_job, run_rules_job
    run_alert_job()
    run_escalation_job()
    run_rules_job()

    return {"data": {"demo_date": new_date, "message": "Demo clock updated and jobs re-run"}}


@router.post("/run-scheduler", dependencies=[Depends(require_roles(SUPER_ADMIN, AUDITOR))])
def trigger_scheduler(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    """Manually trigger all scheduled jobs. Used for demo purposes."""
    from src.jobs.scheduler import run_alert_job, run_escalation_job, run_rules_job
    run_alert_job()
    run_escalation_job()
    run_rules_job()
    write_audit(db, user_id=current_user.id, entity_type="system", entity_id=None,
                action="MANUAL_SCHEDULER_TRIGGER")
    db.commit()
    return {"data": {"message": "All scheduler jobs executed"}}


@router.get("/users", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def list_users(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    users = db.query(User).all()
    return {"data": [
        {
            "id": u.id, "name": u.name, "email": u.email,
            "institution_id": u.institution_id, "active": u.active,
            "roles": [ur.role.name for ur in u.roles],
        }
        for u in users
    ]}


@router.post("/users", dependencies=[Depends(require_roles(SUPER_ADMIN))])
def create_user(body: UserCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    if db.query(User).filter(User.email == body.email.lower()).first():
        raise HTTPException(status_code=409, detail="Email already in use")
    user = User(
        name=body.name, email=body.email.lower(),
        password_hash=hash_password(body.password),
        institution_id=body.institution_id, active=body.active,
    )
    db.add(user)
    db.flush()
    for role_name in body.roles:
        role = db.query(Role).filter(Role.name == role_name).first()
        if role:
            db.add(UserRole(user_id=user.id, role_id=role.id))
    write_audit(db, user_id=current_user.id, entity_type="user", entity_id=user.id,
                action="CREATE_USER", after={"email": user.email, "roles": body.roles})
    db.commit()
    db.refresh(user)
    return {"data": {"id": user.id, "email": user.email}}


@router.get("/settings")
def get_settings_endpoint(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    settings = db.query(SystemSetting).all()
    return {"data": {s.key: s.value for s in settings}}
