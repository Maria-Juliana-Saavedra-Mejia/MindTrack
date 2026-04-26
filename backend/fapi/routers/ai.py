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


def _template_fallback_after_openai_failure(request: Request, user_id: str, reason: str):
    """
    When OpenAI does not return a usable insight, serve the same prepared template
    path used for offline mode so the dashboard still gets compliment/observation/tip.
    """
    try:
        result = request.app.state.ai_service.generate_insights_template(user_id)
        logger.info("%s; served prepared template insight for user %s", reason, user_id)
        return {"insight": result}
    except ValueError as exc:
        logger.warning("Template fallback validation error: %s", exc)
        return JSONResponse(
            content={"error": True, "message": str(exc), "status": 400},
            status_code=400,
        )
    except Exception:
        logger.exception("Template fallback failed after OpenAI error for user %s", user_id)
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "The AI service was unavailable and the backup insight could not be built. "
                    "Check server logs."
                ),
                "status": 503,
            },
            status_code=503,
        )


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
    provider = Config.insight_provider()
    use_template = provider == "local" or (
        provider == "auto" and Config.openai_key_missing()
    )

    if provider == "openai" and Config.openai_key_missing():
        logger.warning("AI generate skipped: OPENAI_API_KEY is not set (insight provider=openai)")
        return JSONResponse(
            content={
                "error": True,
                "message": (
                    "OpenAI is not configured: OPENAI_API_KEY is not set on this server. "
                    "On Render (or your host), add environment variable OPENAI_API_KEY with "
                    "a valid secret key from https://platform.openai.com/api-keys — see README. "
                    "Or set MINDTRACK_INSIGHT_PROVIDER=auto (default) to use free template insights "
                    "when no key is present."
                ),
                "status": 503,
            },
            status_code=503,
        )

    if use_template:
        try:
            result = request.app.state.ai_service.generate_insights_template(user_id)
            logger.info("Generated template insight for user %s", user_id)
            return {"insight": result}
        except ValueError as exc:
            logger.warning("AI template generate validation error: %s", exc)
            return JSONResponse(
                content={"error": True, "message": str(exc), "status": 400},
                status_code=400,
            )
        except Exception as exc:
            logger.exception("Template insight generate failed: %s", exc)
            return JSONResponse(
                content={
                    "error": True,
                    "message": (
                        "Could not generate an insight. Check server logs; "
                        "if log dates in the database look wrong, fix or re-log entries."
                    ),
                    "status": 503,
                },
                status_code=503,
            )

    try:
        result = request.app.state.ai_service.generate_insights_openai(user_id)
        logger.info("Generated OpenAI insight for user %s", user_id)
        return {"insight": result}
    except ValueError as exc:
        msg = str(exc)
        if "No active habits to analyze" in msg:
            logger.warning("AI generate validation error: %s", exc)
            return JSONResponse(
                content={"error": True, "message": msg, "status": 400},
                status_code=400,
            )
        logger.warning("OpenAI returned unusable data (%s); using prepared insight fallback", exc)
        return _template_fallback_after_openai_failure(
            request, user_id, "OpenAI completion missing or invalid"
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
        return _template_fallback_after_openai_failure(
            request, user_id, "OpenAI rate limit or quota exceeded"
        )
    except APIConnectionError as exc:
        logger.warning("OpenAI connection error: %s", exc, exc_info=True)
        return _template_fallback_after_openai_failure(
            request, user_id, "OpenAI connection error"
        )
    except OpenAIError as exc:
        logger.warning("OpenAI error during insight generate: %s", exc, exc_info=True)
        return _template_fallback_after_openai_failure(
            request, user_id, "OpenAI API error"
        )
    except json.JSONDecodeError as exc:
        logger.warning("AI response was not valid JSON: %s", exc, exc_info=True)
        return _template_fallback_after_openai_failure(
            request, user_id, "OpenAI response was not valid JSON"
        )
    except Exception as exc:
        logger.exception("AI generate failed: %s", exc)
        return _template_fallback_after_openai_failure(
            request, user_id, "Unexpected error during OpenAI insight generate"
        )
