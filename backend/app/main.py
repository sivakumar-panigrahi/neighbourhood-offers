from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.claims import router as claims_router
from app.api.routes.offer_parser import router as offer_parser_router
from app.api.routes.offers import router as offers_router
from app.api.routes.redemptions import router as redemptions_router
from app.api.routes.reports import router as reports_router
from app.api.routes.shops import router as shops_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth_router)
app.include_router(shops_router)
app.include_router(offer_parser_router)
app.include_router(offers_router)
app.include_router(claims_router)
app.include_router(redemptions_router)
app.include_router(reports_router)






@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.app_name,
    }