# fapi/routers/auth.py
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request
from fastapi.responses import JSONResponse

from app.config import Config
from app.utils.error_handlers import InvalidCredentialsError, UserAlreadyExistsError
from app.utils.logger import get_logger
from fapi.deps import get_jwt_sub

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(request: Request, body: dict = Body(default_factory=dict)):
    auth = request.app.state.auth_service
    logger.info("Register attempt for %s", body.get("email") if body else None)
    try:
        auth.register_user(body)
        return auth.login_user(
            body.get("email", ""),
            body.get("password", ""),
            _post_register_retries=5,
        )
    except ValueError as exc:
        logger.warning("Register validation error: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 400},
            status_code=400,
        )
    except UserAlreadyExistsError as exc:
        logger.warning("Register duplicate: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 409},
            status_code=409,
        )
    except InvalidCredentialsError as exc:
        logger.warning(
            "Register succeeded but automatic sign-in failed: %s", exc
        )
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "Account created but automatic sign-in failed; "
                    "try logging in manually."
                ),
                "status": 503,
            },
            status_code=503,
        )
    except Exception as exc:
        logger.exception("Register failed with unexpected error")
        payload = {
            "error": True,
            "message": "Registration could not be completed. Try again later.",
            "status": 500,
        }
        if Config._runtime_env_name() != "production":
            payload["detail"] = str(exc)
        return JSONResponse(content=payload, status_code=500)


@router.post("/login")
def login(request: Request, body: dict = Body(default_factory=dict)):
    auth = request.app.state.auth_service
    logger.info("Login attempt for %s", body.get("email") if body else None)
    return auth.login_user(
        body.get("email", ""), body.get("password", "")
    )


@router.post("/logout")
def logout():
    logger.info("Logout request")
    return {"success": True, "message": "Logged out"}


@router.get("/me")
def me(
    request: Request,
    user_id: Annotated[str, Depends(get_jwt_sub)],
):
    auth = request.app.state.auth_service
    logger.info("Profile request for user %s", user_id)
    return {"user": auth.get_user_by_id(user_id)}
