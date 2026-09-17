from fastapi import APIRouter

router = APIRouter()

VERSION = "0.1.0"


@router.get("/health")
async def health_check() -> dict[str, str]:
    return {"status": "ok", "version": VERSION}
