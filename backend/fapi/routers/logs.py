# fapi/routers/logs.py
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger
from fapi.deps import get_jwt_sub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("")
def list_logs(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    try:
        filters = {
            "habit_id": request.query_params.get("habit_id"),
            "date_from": request.query_params.get("from"),
            "date_to": request.query_params.get("to"),
        }
        logs = request.app.state.log_service.get_logs(user_id, filters)
        logger.info("Fetched %s logs for user %s", len(logs), user_id)
        return {"logs": logs}
    except ValueError as exc:
        logger.warning("Log query validation error: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 400},
            status_code=400,
        )


@router.post("", status_code=201)
def create_log(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
    body: dict = Body(default_factory=dict),
):
    try:
        log = request.app.state.log_service.log_habit(
            user_id, body.get("habit_id"), body.get("note")
        )
        logger.info("Created log %s", log.get("id"))
        try:
            habit = request.app.state.habit_service.get_habit(
                str(body.get("habit_id")), user_id
            )
            request.app.state.ai_service.seed_starter_insight_after_first_log(
                user_id, (habit or {}).get("name") or "your habit"
            )
        except Exception:
            logger.exception("Starter coach insight skipped after log create")
        return {"log": log}
    except ValueError as exc:
        logger.warning("Create log validation error: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 400},
            status_code=400,
        )


@router.delete("/{log_id}")
def delete_log(
    request: Request,
    log_id: str,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    request.app.state.log_service.delete_log(log_id, user_id)
    logger.info("Deleted log %s", log_id)
    return {"success": True}


@router.get("/streak/{habit_id}")
def streak(
    request: Request,
    habit_id: str,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    request.app.state.habit_service.get_habit(habit_id, user_id)
    streak_value = request.app.state.log_service.get_streak(habit_id)
    logger.info("Streak for habit %s: %s", habit_id, streak_value)
    return {"habit_id": habit_id, "streak": streak_value}


@router.get("/summary")
def summary(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    data = request.app.state.log_service.get_30_day_summary(user_id)
    logger.info("Summary for user %s with %s habits", user_id, len(data))
    return {"summary": data}
