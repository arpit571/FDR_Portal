"""
Scheduler — runs hourly (demo: every 5 minutes configurable).
Jobs:
  1. Maturity alert generator (90/30/15/7 days)
  2. Escalation checker (7-day alert unacknowledged for 3+ days)
  3. Rule R07, R10 checker on active FDRs
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from src.config.settings import get_settings

settings = get_settings()


def run_alert_job():
    """Generate maturity alerts at configured intervals."""
    from src.config.database import SessionLocal
    from src.config.models import FDR, Alert, Deposit
    from src.config.dates import today as get_today
    from datetime import timedelta

    db = SessionLocal()
    try:
        today = get_today()
        alert_days = settings.alert_days_list
        fdrs = db.query(FDR).filter(
            FDR.status.in_(["Active", "Maturity Alert", "Pending Review"])
        ).all()

        for fdr in fdrs:
            if not fdr.maturity_date:
                continue
            days_left = (fdr.maturity_date - today).days
            for threshold in alert_days:
                if days_left <= threshold:
                    alert_type = f"MATURITY_{threshold}"
                    existing = db.query(Alert).filter(
                        Alert.fdr_id == fdr.id, Alert.alert_type == alert_type
                    ).first()
                    if not existing:
                        alert = Alert(
                            fdr_id=fdr.id,
                            alert_type=alert_type,
                            scheduled_for=fdr.maturity_date - timedelta(days=threshold),
                            channel="in_app",
                        )
                        db.add(alert)
                        # Update FDR status
                        if fdr.status == "Active" and days_left <= 90:
                            fdr.status = "Maturity Alert"

            # Matured with no action
            if fdr.maturity_date < today and fdr.status in ("Active", "Maturity Alert"):
                fdr.status = "Matured - Action Pending"

        db.commit()
    except Exception as e:
        print(f"Alert job error: {e}")
        db.rollback()
    finally:
        db.close()


def run_escalation_job():
    """Escalate unacknowledged 7-day alerts after 3 days."""
    from src.config.database import SessionLocal
    from src.config.models import Alert
    from src.config.dates import today as get_today
    from datetime import timedelta

    db = SessionLocal()
    try:
        today = get_today()
        cutoff = today - timedelta(days=3)
        alerts = db.query(Alert).filter(
            Alert.alert_type == "MATURITY_7",
            Alert.acknowledged_by == None,
            Alert.escalated == False,
            Alert.scheduled_for <= cutoff,
        ).all()
        for a in alerts:
            a.escalated = True
        db.commit()
    except Exception as e:
        print(f"Escalation job error: {e}")
        db.rollback()
    finally:
        db.close()


def run_rules_job():
    """Run R07 and R10 on all relevant FDRs."""
    from src.config.database import SessionLocal
    from src.config.models import FDR, Deposit
    from src.modules.rules.engine import run_rules_for_fdr, RuleContext
    from src.config.dates import today as get_today

    db = SessionLocal()
    try:
        fdrs = db.query(FDR).filter(
            FDR.status.in_(["Active", "Maturity Alert", "Matured - Action Pending"])
        ).all()
        for fdr in fdrs:
            dep = fdr.deposit
            inst = dep.institution
            all_fdrs = db.query(FDR).filter(FDR.deposit_id == dep.id).all()
            ctx = RuleContext(
                db=db, institution_name=inst.name,
                deposit_required_amount=dep.required_amount,
                all_fdrs=all_fdrs, demo_today=get_today(),
            )
            run_rules_for_fdr(fdr, ctx, db)
        db.commit()
    except Exception as e:
        print(f"Rules job error: {e}")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(daemon=True)
    # Run every hour in production; every 5 minutes in demo mode
    interval_minutes = 5
    scheduler.add_job(run_alert_job, IntervalTrigger(minutes=interval_minutes), id="alert_job", replace_existing=True)
    scheduler.add_job(run_escalation_job, IntervalTrigger(minutes=interval_minutes), id="escalation_job", replace_existing=True)
    scheduler.add_job(run_rules_job, IntervalTrigger(minutes=interval_minutes), id="rules_job", replace_existing=True)
    scheduler.start()
    # Run once on startup
    run_alert_job()
    run_escalation_job()
    return scheduler
