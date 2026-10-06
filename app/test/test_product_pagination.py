from app.services import filter_service
from app.services import getCollectionPage_service as collection_service


class FakeResponse:
    def __init__(self, data, count=None):
        self.data = data
        self.count = count


class FakeQuery:
    def __init__(self, table_name, calls):
        self.table_name = table_name
        self.calls = calls
        self.is_single = False

    def select(self, *args, **kwargs):
        self.calls.append(("select", args, kwargs))
        return self

    def eq(self, column, value):
        self.calls.append(("eq", column, value))
        return self

    def in_(self, column, values):
        self.calls.append(("in", column, tuple(values)))
        return self

    def order(self, column, **kwargs):
        self.calls.append(("order", column, kwargs))
        return self

    def range(self, start, end):
        self.calls.append(("range", start, end))
        return self

    def or_(self, expression):
        self.calls.append(("or", expression))
        return self

    def single(self):
        self.is_single = True
        return self

    def execute(self):
        if self.table_name == "categories" and self.is_single:
            return FakeResponse({"id": 3, "slug": "cotton-saree", "name": "Cotton Saree"})
        if self.table_name == "categories":
            return FakeResponse([])
        return FakeResponse([{"id": 41, "product_images": []}], count=41)


class FakeSupabaseAdmin:
    def __init__(self):
        self.calls = []

    def table(self, table_name):
        return FakeQuery(table_name, self.calls)


def test_collection_service_ranges_after_filters_and_returns_pagination(monkeypatch):
    fake_admin = FakeSupabaseAdmin()
    monkeypatch.setattr(collection_service, "supabase_admin", fake_admin)
    monkeypatch.setattr(collection_service, "get_category_filters", lambda _category_id: {})

    result = collection_service.getCollectionPage_service(
        "cotton-saree",
        min_price=500,
        max_price=2000,
        page=2,
        limit=20,
    )

    assert result["products"] == [{"id": 41, "product_images": []}]
    assert result["pagination"] == {
        "page": 2,
        "limit": 20,
        "total": 41,
        "totalPages": 3,
        "hasNextPage": True,
    }

    product_calls = fake_admin.calls
    price_filter_index = next(index for index, call in enumerate(product_calls) if call[0] == "or")
    range_index = next(index for index, call in enumerate(product_calls) if call[0] == "range")
    assert product_calls[price_filter_index][1] == (
        "and(sale_price.gte.500.0,sale_price.lte.2000.0),"
        "and(sale_price.is.null,price.gte.500.0,price.lte.2000.0),"
        "and(sale_price.is.null,price.is.null)"
    )
    assert product_calls[range_index] == ("range", 20, 39)
    assert price_filter_index < range_index


def test_get_category_filters_falls_back_to_product_filter_values(monkeypatch):
    class FakeGroupsQuery:
        def __init__(self):
            self.data = [{"id": 7, "key": "brand", "name": "Brand", "type": "checkbox", "active": True, "display_order": 1}]

        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def order(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse(self.data)

    class FakeCategoryOptionsQuery:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse([])

    class FakeProductIdsQuery:
        def select(self, *_args, **_kwargs):
            return self

        def eq(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse([{"id": 22}, {"id": 23}])

    class FakeProductFilterValuesQuery:
        def select(self, *_args, **_kwargs):
            return self

        def in_(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse([
                {"product_id": 22, "filter_option_id": 100},
                {"product_id": 23, "filter_option_id": 100},
                {"product_id": 23, "filter_option_id": 101},
            ])

    class FakeFilterOptionsQuery:
        def select(self, *_args, **_kwargs):
            return self

        def in_(self, *_args, **_kwargs):
            return self

        def execute(self):
            return FakeResponse([
                {"id": 100, "group_id": 7, "name": "Aurelia", "slug": "aurelia", "hex_code": None, "value": None, "display_order": 1},
                {"id": 101, "group_id": 7, "name": "Mira", "slug": "mira", "hex_code": None, "value": None, "display_order": 2},
            ])

    def fake_table(name):
        if name == "filter_groups":
            return FakeGroupsQuery()
        if name == "category_filter_options":
            return FakeCategoryOptionsQuery()
        if name == "products":
            return FakeProductIdsQuery()
        if name == "product_filter_values":
            return FakeProductFilterValuesQuery()
        if name == "filter_options":
            return FakeFilterOptionsQuery()
        raise AssertionError(name)

    monkeypatch.setattr(filter_service, "supabase_admin", type("FakeSupabaseAdmin", (), {"table": staticmethod(fake_table)})())

    filters = filter_service.get_category_filters(998)

    assert filters["brand"]["displayName"] == "Brand"
    assert {option["name"] for option in filters["brand"]["options"]} == {"Aurelia", "Mira"}