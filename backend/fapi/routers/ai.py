# fapi/routers/ai.py
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger
from fapi.deps import get_jwt_sub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.get("/insights")
def insights(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    data = request.app.state.ai_service.get_latest_insights(user_id)
    logger.info("Fetched AI insights for user %s", user_id)
    return {"insight": data}


@router.post("/generate")
def generate(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    try:
        result = request.app.state.ai_service.generate_insights(user_id)
        logger.info("Generated AI insight for user %s", user_id)
        return {"insight": result}
    except ValueError as exc:
        logger.warning("AI generate validation error: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 400},
            status_code=400,
        )
