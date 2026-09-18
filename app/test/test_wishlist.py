from app.services.wishlist_service import get_user_wishlist_service


def test_get_user_wishlist_service_exists():
    assert callable(get_user_wishlist_service)
