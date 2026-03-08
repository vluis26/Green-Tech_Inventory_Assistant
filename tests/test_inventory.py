"""
Pytest tests for the Green-Tech Inventory Assistant API.
Run from repo root:  pytest tests/ -v
"""
import os
import sys
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# Make backend importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import database
import main as app_module


@pytest_asyncio.fixture
async def client(tmp_path):
    """Use a temp file DB so every aiosqlite.connect() sees the same tables."""
    db_file = str(tmp_path / "test.db")
    original_db = database.DB_PATH
    database.DB_PATH = db_file
    try:
        await database.init_db()
        transport = ASGITransport(app=app_module.app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        database.DB_PATH = original_db


# Happy path: create an item and verify it appears in GET /items

@pytest.mark.asyncio
async def test_create_and_list_item(client: AsyncClient):
    payload = {
        "name": "Recycled Copy Paper",
        "category": "office supplies",
        "quantity": 500.0,
        "unit": "sheets",
        "expiry_date": None,
        "daily_usage_rate": 50.0,
        "threshold": 100.0,
    }

    create_resp = await client.post("/items", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["name"] == "Recycled Copy Paper"
    assert created["category"] == "office supplies"
    assert created["quantity"] == 500.0
    assert "id" in created
    assert "sustainability_score" in created
    assert 0 <= created["sustainability_score"] <= 100

    list_resp = await client.get("/items")
    assert list_resp.status_code == 200
    ids = [i["id"] for i in list_resp.json()]
    assert created["id"] in ids


# Edge case: create item with quantity 0 — appears in low-stock dashboard

@pytest.mark.asyncio
async def test_create_item_zero_quantity(client: AsyncClient):
    payload = {
        "name": "Empty Hand Sanitizer",
        "category": "cleaning",
        "quantity": 0.0,
        "unit": "bottles",
        "expiry_date": "2026-12-31",
        "daily_usage_rate": 1.0,
        "threshold": 5.0,
    }

    create_resp = await client.post("/items", json=payload)
    assert create_resp.status_code == 201, create_resp.text
    created = create_resp.json()
    assert created["quantity"] == 0.0

    dash_resp = await client.get("/dashboard")
    assert dash_resp.status_code == 200
    dashboard = dash_resp.json()
    low_stock_ids = [i["id"] for i in dashboard["low_stock"]]
    assert created["id"] in low_stock_ids
