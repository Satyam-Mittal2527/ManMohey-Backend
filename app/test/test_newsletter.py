import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes import newsletter_routes
from app.services import newsletter_service


def make_test_client():
    app = FastAPI()
    app.include_router(newsletter_routes.router)
    return TestClient(app)


def test_empty_and_invalid_email_are_rejected_before_service_call(monkeypatch):
    async def fail_if_called(_email):
        raise AssertionError("Klaviyo must not be called for invalid input")

    monkeypatch.setattr(newsletter_routes, "subscribe_to_newsletter", fail_if_called)
    client = make_test_client()

    assert client.post("/api/newsletter/subscribe", json={"email": ""}).status_code == 422
    assert client.post("/api/newsletter/subscribe", json={"email": "not-an-email"}).status_code == 422
    assert client.post("/api/newsletter/subscribe", json={}).status_code == 422


def test_valid_email_returns_double_opt_in_message(monkeypatch):
    async def accepted(email):
        assert email == "customer@example.com"
        return True

    monkeypatch.setattr(newsletter_routes, "subscribe_to_newsletter", accepted)
    response = make_test_client().post(
        "/api/newsletter/subscribe",
        json={"email": " customer@example.com "},
    )

    assert response.status_code == 200
    assert response.json() == {
        "success": True,
        "message": (
            "Subscription request received. Please check your inbox to confirm "
            "your subscription."
        ),
    }


def test_existing_subscriber_is_handled_successfully(monkeypatch):
    async def already_subscribed(_email):
        return False

    monkeypatch.setattr(newsletter_routes, "subscribe_to_newsletter", already_subscribed)
    response = make_test_client().post(
        "/api/newsletter/subscribe",
        json={"email": "customer@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert "already subscribed" in response.json()["message"]


def test_klaviyo_request_contains_subscription_and_private_headers(monkeypatch):
    monkeypatch.setattr(newsletter_service.settings, "KLAVIYO_PRIVATE_API_KEY", "test-private-key")
    monkeypatch.setattr(newsletter_service.settings, "KLAVIYO_NEWSLETTER_LIST_ID", "XyrkBT")
    monkeypatch.setattr(newsletter_service.settings, "KLAVIYO_API_REVISION", "2026-07-15")
    captured = {}

    class AcceptedResponse:
        status_code = 202

    class FakeAsyncClient:
        def __init__(self, timeout, follow_redirects):
            assert timeout == 10.0
            assert follow_redirects is True

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, url, *, headers, json):
            captured.update(url=url, headers=headers, payload=json)
            return AcceptedResponse()

    monkeypatch.setattr(newsletter_service.httpx, "AsyncClient", FakeAsyncClient)

    assert asyncio.run(
        newsletter_service.subscribe_to_newsletter("customer@example.com")
    ) is True
    assert captured["url"] == newsletter_service.KLAVIYO_SUBSCRIBE_URL
    assert captured["headers"] == {
        "Authorization": "Klaviyo-API-Key test-private-key",
        "revision": "2026-07-15",
        "Content-Type": "application/vnd.api+json",
        "Accept": "application/vnd.api+json",
    }
    payload = captured["payload"]["data"]
    assert payload["attributes"]["historical_import"] is False
    assert payload["attributes"]["profiles"]["data"][0]["attributes"] == {
        "email": "customer@example.com",
        "subscriptions": {
            "email": {"marketing": {"consent": "SUBSCRIBED"}}
        },
    }
    assert payload["relationships"]["list"]["data"] == {
        "type": "list",
        "id": "XyrkBT",
    }
    assert payload["attributes"]["custom_source"] == "ManMohey Website Newsletter Signup"


def test_klaviyo_duplicate_is_treated_as_already_subscribed(monkeypatch):
    monkeypatch.setattr(newsletter_service.settings, "KLAVIYO_PRIVATE_API_KEY", "test-private-key")

    class DuplicateResponse:
        status_code = 409

    class FakeAsyncClient:
        def __init__(self, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return DuplicateResponse()

    monkeypatch.setattr(newsletter_service.httpx, "AsyncClient", FakeAsyncClient)

    assert asyncio.run(
        newsletter_service.subscribe_to_newsletter("customer@example.com")
    ) is False


def test_klaviyo_failure_returns_only_friendly_error(monkeypatch):
    async def fail(_email):
        raise newsletter_service.NewsletterServiceError("Klaviyo private diagnostic")

    monkeypatch.setattr(newsletter_routes, "subscribe_to_newsletter", fail)
    response = make_test_client().post(
        "/api/newsletter/subscribe",
        json={"email": "customer@example.com"},
    )

    assert response.status_code == 502
    assert response.json() == {
        "detail": "We couldn’t subscribe you right now. Please try again later."
    }
    assert "Klaviyo private diagnostic" not in response.text
    assert "test-private-key" not in response.text
