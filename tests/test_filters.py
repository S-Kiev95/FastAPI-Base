"""Tests del sistema de filtros avanzados."""


class TestBasicFilter:
    def test_filter_by_email_contains(self, client, sample_users):
        response = client.post(
            "/users/filter",
            json={
                "conditions": [
                    {"field": "email", "operator": "icontains", "value": "gmail"}
                ]
            },
        )
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 2
        assert all("gmail" in u["email"] for u in users)

    def test_filter_by_provider(self, client, sample_users):
        response = client.post(
            "/users/filter",
            json={
                "conditions": [
                    {"field": "provider", "operator": "eq", "value": "google"}
                ]
            },
        )
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 3
        assert all(u["provider"] == "google" for u in users)


class TestMultipleConditions:
    def test_and_conditions(self, client, sample_users):
        response = client.post(
            "/users/filter",
            json={
                "conditions": [
                    {"field": "email", "operator": "icontains", "value": "gmail"},
                    {"field": "provider", "operator": "eq", "value": "google"},
                ],
                "operator": "and",
            },
        )
        assert response.status_code == 200
        users = response.json()
        # Solo Alice es google + gmail
        assert len(users) == 1
        assert users[0]["email"] == "alice@gmail.com"

    def test_or_conditions(self, client, sample_users):
        response = client.post(
            "/users/filter",
            json={
                "conditions": [
                    {"field": "email", "operator": "icontains", "value": "gmail"},
                    {"field": "email", "operator": "icontains", "value": "yahoo"},
                ],
                "operator": "or",
            },
        )
        assert response.status_code == 200
        users = response.json()
        assert len(users) == 3  # alice, charlie (gmail) + bob (yahoo)


class TestPagination:
    def test_paginated_filter(self, client, sample_users):
        response = client.post(
            "/users/filter/paginated",
            json={
                "order_by": "email",
                "order_direction": "asc",
                "limit": 2,
                "offset": 0,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert result["total"] == 4
        assert result["limit"] == 2
        assert len(result["data"]) == 2
        assert result["has_more"] is True

    def test_paginated_second_page(self, client, sample_users):
        response = client.post(
            "/users/filter/paginated",
            json={
                "order_by": "email",
                "order_direction": "asc",
                "limit": 2,
                "offset": 2,
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["data"]) == 2
        assert result["has_more"] is False


class TestOrdering:
    def test_order_by_name_asc(self, client, sample_users):
        response = client.post(
            "/users/filter",
            json={"order_by": "name", "order_direction": "asc", "limit": 10},
        )
        assert response.status_code == 200
        users = response.json()
        names = [u["name"] for u in users]
        assert names == sorted(names)

    def test_order_by_name_desc(self, client, sample_users):
        response = client.post(
            "/users/filter",
            json={"order_by": "name", "order_direction": "desc", "limit": 10},
        )
        assert response.status_code == 200
        users = response.json()
        names = [u["name"] for u in users]
        assert names == sorted(names, reverse=True)
