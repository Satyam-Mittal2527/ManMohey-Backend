import logging

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)

KLAVIYO_SUBSCRIBE_URL = (
    "https://a.klaviyo.com/api/profile-subscription-bulk-create-jobs/"
)


class NewsletterConfigurationError(Exception):
    """Raised when newsletter integration settings are incomplete."""


class NewsletterServiceError(Exception):
    """Raised when Klaviyo cannot accept a newsletter subscription."""


def _subscription_response_diagnostics(response: httpx.Response) -> dict:
    """Return only response fields useful for async-job diagnostics."""
    response_headers = getattr(response, "headers", {})
    relevant_headers = {
        name: response_headers[name]
        for name in ("location", "content-location", "x-klaviyo-request-id", "x-request-id", "retry-after")
        if name in response_headers
    }

    try:
        body = response.json()
    except (ValueError, AttributeError):
        body = {}

    if not isinstance(body, dict):
        body = {}

    job = body.get("data")
    if not isinstance(job, dict):
        job = {}
    attributes = job.get("attributes")
    if not isinstance(attributes, dict):
        attributes = {}

    raw_errors = body.get("errors", attributes.get("errors", []))
    errors = [
        {
            key: error[key]
            for key in ("code", "title", "detail")
            if key in error
        }
        for error in raw_errors
        if isinstance(error, dict)
    ] if isinstance(raw_errors, list) else []

    return {
        "headers": relevant_headers,
        "job_id": job.get("id") or body.get("job_id"),
        "job_status": attributes.get("status") or body.get("status"),
        "errors": errors,
    }


def _is_duplicate_subscription(response: httpx.Response) -> bool:
    if response.status_code == 409:
        return True

    try:
        errors = response.json().get("errors", [])
    except (ValueError, AttributeError):
        return False

    for error in errors:
        if not isinstance(error, dict):
            continue
        text = " ".join(
            str(error.get(key, ""))
            for key in ("code", "title", "detail")
        ).lower()
        if "duplicate_subscription" in text or (
            "already" in text
            and ("subscribed" in text or "in the list" in text or "on the list" in text)
        ):
            return True

    return False


async def subscribe_to_newsletter(email: str) -> bool:
    """Submit an email subscription to the configured Klaviyo list.

    Returns True for a new accepted request and False when Klaviyo identifies
    the profile as already subscribed.
    """
    api_key = settings.KLAVIYO_PRIVATE_API_KEY
    list_id = settings.KLAVIYO_NEWSLETTER_LIST_ID
    revision = settings.KLAVIYO_API_REVISION
    if not api_key or not list_id or not revision:
        raise NewsletterConfigurationError("Klaviyo settings are incomplete")

    headers = {
        "Authorization": f"Klaviyo-API-Key {api_key}",
        "revision": revision,
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json",
    }
    payload = {
        "data": {
            "type": "profile-subscription-bulk-create-job",
            "attributes": {
                "custom_source": "ManMohey Website Newsletter Signup",
                # Keep Klaviyo's list opt-in policy in control. Historical
                # imports bypass double opt-in and must remain disabled here.
                "historical_import": False,
                "profiles": {
                    "data": [
                        {
                            "type": "profile",
                            "attributes": {
                                "email": email,
                                "subscriptions": {
                                    "email": {
                                        "marketing": {
                                            "consent": "SUBSCRIBED"
                                        }
                                    }
                                },
                            },
                        }
                    ]
                },
            },
            "relationships": {
                "list": {
                    "data": {
                        "type": "list",
                        "id": list_id,
                    }
                }
            },
        }
    }

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True,
        ) as client:
            response = await client.post(
                KLAVIYO_SUBSCRIBE_URL,
                headers=headers,
                json=payload,
            )
            diagnostics = _subscription_response_diagnostics(response)
            logger.info(
                "Klaviyo newsletter response: status=%s headers=%s job_id=%s "
                "job_status=%s errors=%s",
                response.status_code,
                diagnostics["headers"],
                diagnostics["job_id"],
                diagnostics["job_status"],
                diagnostics["errors"],
            )
    except httpx.RequestError as exc:
        raise NewsletterServiceError(
            "Klaviyo request failed"
        ) from exc

    if 200 <= response.status_code < 300:
        return True
    if _is_duplicate_subscription(response):
        return False

    raise NewsletterServiceError(
        f"Klaviyo rejected newsletter subscription (HTTP {response.status_code})"
    )
