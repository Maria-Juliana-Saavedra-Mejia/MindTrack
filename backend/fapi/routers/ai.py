# fapi/routers/ai.py
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from openai import APIConnectionError, AuthenticationError, OpenAIError, RateLimitError

from app.config import Config
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
    if Config.openai_key_missing():
        logger.warning("AI generate skipped: OPENAI_API_KEY is not set")
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "OpenAI is not configured: OPENAI_API_KEY is not set on this server. "
                    "On Render (or your host), add environment variable OPENAI_API_KEY with "
                    "a valid secret key from https://platform.openai.com/api-keys — see README."
                ),
                "status": 503,
            },
            status_code=503,
        )
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
    except AuthenticationError as exc:
        logger.warning("OpenAI authentication failed: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "OpenAI rejected this API key (invalid or revoked). Check OPENAI_API_KEY "
                    "on the server for typos or extra spaces; create a new key at "
                    "https://platform.openai.com/api-keys — see README."
                ),
                "status": 502,
            },
            status_code=502,
        )
    except RateLimitError as exc:
        logger.warning("OpenAI rate limit: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "OpenAI rate limit or quota exceeded. Wait a minute and try again; "
                    "check billing and usage at https://platform.openai.com — see README."
                ),
                "status": 502,
            },
            status_code=502,
        )
    except APIConnectionError as exc:
        logger.warning("OpenAI connection error: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "Could not reach OpenAI (network error). Retry shortly; on free hosts "
                    "cold starts can interrupt outbound requests — see README."
                ),
                "status": 502,
            },
            status_code=502,
        )
    except OpenAIError as exc:
        logger.warning("OpenAI error during insight generate: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "AI service error from OpenAI. Verify OPENAI_API_KEY, billing, and model "
                    "access; check server logs for details — see README."
                ),
                "status": 502,
            },
            status_code=502,
        )
    except json.JSONDecodeError as exc:
        logger.warning("AI response was not valid JSON: %s", exc, exc_info=True)
        return JSONResponse(
            content={
                "error": True,
                "message": "The AI returned an unexpected format. Please try again.",
                "status": 502,
            },
            status_code=502,
        )
    except Exception as exc:
        logger.exception("AI generate failed: %s", exc)
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "Could not generate an insight. Check OPENAI_API_KEY and server "
                    "logs; if log dates in the database look wrong, fix or re-log entries."
                ),
                "status": 503,
            },
            status_code=503,
        )
