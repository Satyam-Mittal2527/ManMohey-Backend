from app.services.getCollectionPage_service import _resolve_product_id, get_product_reviews_service


def test_resolve_product_id_handles_single_row_dict_result(monkeypatch):
    class FakeResponse:
        def __init__(self, data=None):
            self.data = data

    class FakeProductsTable:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, column, value):
            return self

        def single(self):
            return self

        def execute(self):
            return FakeResponse({"id": 13})

    monkeypatch.setattr("app.services.getCollectionPage_service.supabase_admin.table", lambda *_args, **_kwargs: FakeProductsTable())

    assert _resolve_product_id("banarasi-silk-saree-royal-maroon") == 13


def test_get_product_reviews_service_builds_summary_and_images(monkeypatch):
    class FakeResponse:
        def __init__(self, data=None, count=None):
            self.data = data or []
            self.count = count

    class FakeProductsTable:
        def __init__(self):
            self.calls = []

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, column, value):
            self.calls.append(("eq", column, value))
            return self

        def single(self):
            return self

        def execute(self):
            if self.calls and self.calls[-1][1] == "id":
                return FakeResponse([{"id": 13, "slug": "banarasi-silk-saree-royal-maroon"}])
            if self.calls and self.calls[-1][1] == "slug":
                return FakeResponse([{"id": 13, "slug": "banarasi-silk-saree-royal-maroon"}])
            return FakeResponse([])

    class FakeReviewsTable:
        def __init__(self):
            self.calls = []

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, column, value):
            self.calls.append(("eq", column, value))
            return self

        def order(self, *_args, **_kwargs):
            return self

        def range(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse([
                {"id": "r2", "product_id": 13, "user_id": "u2", "rating": 4, "comment": "Second review", "is_verified_purchase": True, "is_approved": True, "created_at": "2026-10-02T00:00:00+00:00"},
                {"id": "r1", "product_id": 13, "user_id": "u1", "rating": 5, "comment": "First review", "is_verified_purchase": True, "is_approved": True, "created_at": "2026-10-04T00:00:00+00:00"},
            ], count=2)

    class FakeImagesTable:
        def __init__(self):
            pass

        def select(self, *_args, **_kwargs):
            return self

        def in_(self, column, values):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse([
                {"id": "i1", "review_id": "r1", "image_url": "https://cdn.example.com/r1.png", "display_order": 1},
                {"id": "i2", "review_id": "r2", "image_url": "https://cdn.example.com/r2.png", "display_order": 1},
            ])

    class FakeProfilesTable:
        def __init__(self):
            pass

        def in_(self, column, values):
            return self

        def select(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse([
                {"id": "u1", "first_name": "Satyam", "last_name": "Mittal"},
                {"id": "u2", "first_name": "Aarav", "last_name": "Sharma"},
            ])

    def fake_table(name):
        if name == "products":
            return FakeProductsTable()
        if name == "reviews":
            return FakeReviewsTable()
        if name == "review_images":
            return FakeImagesTable()
        if name == "profiles":
            return FakeProfilesTable()
        raise AssertionError(f"unexpected table: {name}")

    class FakeStorageBucket:
        def get_public_url(self, value):
            return value

    monkeypatch.setattr("app.services.getCollectionPage_service.supabase_admin.table", fake_table)
    monkeypatch.setattr("app.services.getCollectionPage_service.supabase.storage.from_", lambda _: FakeStorageBucket())

    result = get_product_reviews_service(13)

    assert result["summary"]["average_rating"] == 4.5
    assert result["summary"]["total_reviews"] == 2
    assert result["summary"]["rating_distribution"]["5"] == 1
    assert result["summary"]["rating_distribution"]["4"] == 1
    assert result["reviews"][0]["user"]["first_name"] == "Satyam"
    assert result["reviews"][0]["images"][0]["image_url"] == "https://cdn.example.com/r1.png"
