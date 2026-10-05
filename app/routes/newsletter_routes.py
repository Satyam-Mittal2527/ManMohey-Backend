import logging

from fastapi import APIRouter, HTTPException

from app.schemas.newsletter import NewsletterSubscribeRequest
from app.services.newsletter_service import (
    NewsletterConfigurationError,
    NewsletterServiceError,
    subscribe_to_newsletter,
)


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/newsletter",
    tags=["Newsletter"],
)


@router.post("/subscribe")
async def subscribe(payload: NewsletterSubscribeRequest):
    try:
        already_subscribed = not await subscribe_to_newsletter(payload.email)
    except NewsletterConfigurationError:
        logger.error("Newsletter integration is not configured")
        raise HTTPException(
            status_code=503,
            detail="Newsletter signup is temporarily unavailable. Please try again later.",
        ) from None
    except NewsletterServiceError:
        logger.warning("Klaviyo newsletter subscription request failed")
        raise HTTPException(
            status_code=502,
            detail="We couldn’t subscribe you right now. Please try again later.",
        ) from None
    except Exception:
        logger.exception("Unexpected newsletter subscription failure")
        raise HTTPException(
            status_code=500,
            detail="Newsletter signup failed. Please try again later.",
        ) from None

    if already_subscribed:
        return {
            "success": True,
            "message": "You’re already subscribed to the ManMohey newsletter.",
        }

    return {
        "success": True,
        "message": (
            "Subscription request received. Please check your inbox to confirm "
            "your subscription."
        ),
    }
