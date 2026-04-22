# fapi/routers/habits.py
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from app.utils.logger import get_logger
from fapi.deps import get_jwt_sub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/habits", tags=["habits"])


@router.get("")
def list_habits(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    active_only = (
        request.query_params.get("active_only", "false").lower() == "true"
    )
    habits = request.app.state.habit_service.get_habits(user_id, active_only=active_only)
    logger.info("Listed habits for user %s", user_id)
    return {"habits": habits}


@router.post("", status_code=201)
def create_habit(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
    body: dict = Body(default_factory=dict),
):
    try:
        habit = request.app.state.habit_service.create_habit(user_id, body)
        logger.info("Created habit %s", habit.get("id"))
        return {"habit": habit}
    except ValueError as exc:
        logger.warning("Create habit validation error: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 400},
            status_code=400,
        )


@router.get("/{habit_id}")
def get_habit(
    request: Request,
    habit_id: str,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    habit = request.app.state.habit_service.get_habit(habit_id, user_id)
    logger.info("Fetched habit %s", habit_id)
    return {"habit": habit}


@router.put("/{habit_id}")
def update_habit(
    request: Request,
    habit_id: str,
    user_id: Annotated[str, Depends(get_jwt_sub)],
    body: dict = Body(default_factory=dict),
):
    try:
        habit = request.app.state.habit_service.update_habit(habit_id, user_id, body)
        logger.info("Updated habit %s", habit_id)
        return {"habit": habit}
    except ValueError as exc:
        logger.warning("Update habit validation error: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 400},
            status_code=400,
        )


@router.delete("/{habit_id}")
def delete_habit(
    request: Request,
    habit_id: str,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    request.app.state.habit_service.delete_habit(habit_id, user_id)
    logger.info("Deleted habit %s", habit_id)
    return {"success": True}
