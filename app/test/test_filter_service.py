from app.services.filter_service import (
    count_products_for_filter_options,
    get_matching_product_ids,
    parse_selected_filter_values,
)


def test_parse_selected_filter_values_handles_csv_and_repeated_params():
    query_params = {
        "fabric": ["5,6", "7"],
        "color": "25,26",
        "size": ["10", "11"],
    }

    result = parse_selected_filter_values(query_params)

    assert result == {
        "fabric": [5, 6, 7],
        "color": [25, 26],
        "size": [10, 11],
    }


def test_parse_selected_filter_values_ignores_pagination_parameters():
    result = parse_selected_filter_values({"page": "2", "limit": "20", "fabric": "5"})

    assert result == {"fabric": [5]}


def test_get_matching_product_ids_uses_or_within_group_and_and_across_groups(monkeypatch):
    class FakeResponse:
        def __init__(self, rows):
            self.data = rows

    class FakeTable:
        def __init__(self, rows_by_call):
            self.rows_by_call = rows_by_call
            self.calls = []

        def select(self, _):
            return self

        def in_(self, column, values):
            normalized = tuple(sorted(values))
            self.calls.append((column, normalized))
            return self

        def order(self, _column):
            return self

        def range(self, _start, _end):
            return self

        def execute(self):
            key = self.calls[-1] if self.calls else None
            return FakeResponse(self.rows_by_call.get(key, []))

    rows_by_call = {
        ("filter_option_id", (5, 6)): [
            {"product_id": 1},
            {"product_id": 2},
            {"product_id": 3},
        ],
        ("filter_option_id", (25, 26)): [
            {"product_id": 2},
            {"product_id": 3},
            {"product_id": 4},
        ],
        ("filter_option_id", (10, 11)): [
            {"product_id": 3},
            {"product_id": 4},
        ],
    }

    monkeypatch.setattr(
        "app.services.filter_service.supabase_admin.table",
        lambda _: FakeTable(rows_by_call),
    )

    selected = {"fabric": [5, 6], "color": [25, 26], "size": [10, 11]}

    assert get_matching_product_ids(selected) == {3}


def test_count_products_for_filter_options_counts_only_category_products(monkeypatch):
    class FakeResponse:
        def __init__(self, rows):
            self.data = rows

    class FakeTable:
        def __init__(self, table_name, rows_by_call):
            self.table_name = table_name
            self.rows_by_call = rows_by_call
            self.calls = []

        def select(self, _):
            return self

        def eq(self, column, value):
            self.calls.append(("eq", column, value))
            return self

        def in_(self, column, values):
            normalized = tuple(sorted(values))
            self.calls.append(("in", column, normalized))
            return self

        def execute(self):
            if self.table_name == "products":
                return FakeResponse([
                    {"id": 1},
                    {"id": 2},
                    {"id": 3},
                    {"id": 4},
                ])
            return FakeResponse([
                {"product_id": 1, "filter_option_id": 5},
                {"product_id": 2, "filter_option_id": 5},
                {"product_id": 2, "filter_option_id": 6},
                {"product_id": 3, "filter_option_id": 5},
                {"product_id": 4, "filter_option_id": 7},
            ])

    def fake_table(name):
        return FakeTable(name, {})

    monkeypatch.setattr("app.services.filter_service.supabase_admin.table", fake_table)

    result = count_products_for_filter_options(1, [5, 6, 7])

    assert result == {5: 3, 6: 1, 7: 1}
