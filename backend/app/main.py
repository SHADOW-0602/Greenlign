from fastapi import FastAPI

from app.api.calculation import router as calculation_router
from app.api.classification import router as classification_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router

app = FastAPI(
    title="Greenlign API",
    version="0.1.0",
    description="AI-assisted GHG accounting platform",
)

app.include_router(health_router)
app.include_router(ingestion_router, prefix="/api/ingestion", tags=["ingestion"])
app.include_router(
    classification_router,
    prefix="/api/classification",
    tags=["classification"],
)
app.include_router(
    calculation_router,
    prefix="/api/calculations",
    tags=["calculations"],
)
