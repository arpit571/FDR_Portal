"""
FastAPI application — registers all routers, middleware, and startup events.
"""
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from src.config.settings import get_settings
from src.config.database import engine, Base

# Import all models to ensure they are registered
import src.config.models  # noqa: F401

# Import all routers
from src.auth.router import router as auth_router
from src.modules.institutions.router import router as institutions_router
from src.modules.banks.router import router as banks_router
from src.modules.regulatory.router import router as regulatory_router
from src.modules.deposits.router import router as deposits_router
from src.modules.fdrs.router import router as fdrs_router
from src.modules.documents.router import router as documents_router
from src.modules.ocr.router import router as ocr_router
from src.modules.review.router import router as review_router
from src.modules.verification.router import router as verification_router
from src.modules.rules.router import router as rules_router
from src.modules.discrepancies.router import router as discrepancies_router
from src.modules.alerts.router import router as alerts_router
from src.modules.renewals.router import router as renewals_router
from src.modules.releases.router import router as releases_router
from src.modules.dashboard.router import router as dashboard_router
from src.modules.reports.router import router as reports_router
from src.modules.admin.router import router as admin_router
from src.audit.router import router as audit_router
from src.jobs.scheduler import start_scheduler

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup
    Base.metadata.create_all(bind=engine)
    # Ensure storage directory exists
    os.makedirs(settings.STORAGE_PATH, exist_ok=True)
    # Start background scheduler
    scheduler = start_scheduler()
    yield
    scheduler.shutdown(wait=False)


app = FastAPI(
    title="FDR SmartTrack Portal",
    description="AICTE Security Deposit / FDR Management Portal — SIH 26265",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global error handler — never expose stack traces in production
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    import traceback
    # Log to stderr in dev
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"error": "An internal server error occurred.", "data": None},
    )


# Register all routers
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(institutions_router, prefix="/api/institutions", tags=["Institutions"])
app.include_router(banks_router, prefix="/api/banks", tags=["Banks"])
app.include_router(regulatory_router, prefix="/api/regulatory-rules", tags=["Regulatory Rules"])
app.include_router(deposits_router, prefix="/api/deposits", tags=["Deposits"])
app.include_router(fdrs_router, prefix="/api/fdrs", tags=["FDRs"])
app.include_router(documents_router, prefix="/api/documents", tags=["Documents"])
app.include_router(ocr_router, prefix="/api/ocr-fields", tags=["OCR"])
app.include_router(review_router, prefix="/api/review-queue", tags=["Review Queue"])
app.include_router(verification_router, prefix="/api", tags=["Bank Verification"])
app.include_router(rules_router, prefix="/api/rules", tags=["Discrepancy Rules"])
app.include_router(discrepancies_router, prefix="/api/discrepancies", tags=["Discrepancies"])
app.include_router(alerts_router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(renewals_router, prefix="/api/renewals", tags=["Renewals"])
app.include_router(releases_router, prefix="/api/releases", tags=["Releases"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
app.include_router(reports_router, prefix="/api/reports", tags=["Reports"])
app.include_router(admin_router, prefix="/api/admin", tags=["Admin"])
app.include_router(audit_router, prefix="/api/audit", tags=["Audit"])


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "FDR SmartTrack Portal"}
