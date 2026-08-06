from fastapi import APIRouter

from app.api.routes import analytics, audit, auth, cases, evidence, health, narratives, reports


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(audit.router)
api_router.include_router(auth.router)
api_router.include_router(cases.router)
api_router.include_router(evidence.router)
api_router.include_router(analytics.router)
api_router.include_router(narratives.router)
api_router.include_router(reports.router)
