import csv
import io
import logging
from datetime import datetime, UTC
from typing import Optional, List

import aiosqlite
from fastapi import APIRouter, HTTPException, Query, UploadFile, File

import database
from models import Item, ItemCreate, ItemUpdate, ParseRequest, ParsedItem
from services.scoring import compute_sustainability_score
from services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter()

CSV_COLUMNS = {"name", "category", "quantity", "unit", "expiry_date", "daily_usage_rate", "threshold"}


@router.get("/items", response_model=List[Item])
async def list_items(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    async with aiosqlite.connect(database.DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM items WHERE 1=1"
        params: list = []
        if search:
            query += " AND name LIKE ?"
            params.append(f"%{search}%")
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC"
        async with db.execute(query, params) as cursor:
            rows = await cursor.fetchall()
    return [dict(r) for r in rows]


@router.post("/items/import")
async def import_csv(file: UploadFile = File(...)):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be a .csv")

    content = await file.read()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV has no headers")

    missing = CSV_COLUMNS - {"expiry_date"} - set(reader.fieldnames)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(sorted(missing))}")

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no data rows")

    created_at = datetime.now(UTC).isoformat()
    inserted = 0
    errors = []

    async with aiosqlite.connect(database.DB_PATH) as db:
        for i, row in enumerate(rows, start=2):
            try:
                name = row["name"].strip()
                category = row["category"].strip().lower()
                quantity = float(row["quantity"])
                unit = row["unit"].strip()
                expiry_date = row.get("expiry_date", "").strip() or None
                daily_usage_rate = float(row["daily_usage_rate"])
                threshold = float(row["threshold"])
            except (ValueError, KeyError) as e:
                errors.append(f"Row {i}: {e}")
                continue

            score = compute_sustainability_score(category, quantity, daily_usage_rate, threshold)
            await db.execute(
                """INSERT INTO items
                   (name, category, quantity, unit, expiry_date, daily_usage_rate, threshold, sustainability_score, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (name, category, quantity, unit, expiry_date, daily_usage_rate, threshold, score, created_at),
            )
            inserted += 1

        await db.commit()

    return {"inserted": inserted, "errors": errors}


@router.post("/items/parse-description", response_model=ParsedItem)
async def parse_description(payload: ParseRequest):
    if not ai_service.ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")
    try:
        data = await ai_service.parse_description_ai(payload.description)
        return ParsedItem(**{k: v for k, v in data.items() if v is not None})
    except Exception as e:
        logger.error("parse-description failed: %s: %s", type(e).__name__, e)
        raise HTTPException(status_code=502, detail=f"AI parsing failed: {e}")


@router.post("/items", response_model=Item, status_code=201)
async def create_item(payload: ItemCreate):
    score = compute_sustainability_score(
        payload.category, payload.quantity, payload.daily_usage_rate, payload.threshold
    )
    created_at = datetime.now(UTC).isoformat()
    async with aiosqlite.connect(database.DB_PATH) as db:
        cursor = await db.execute(
            """INSERT INTO items
               (name, category, quantity, unit, expiry_date, daily_usage_rate, threshold, sustainability_score, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                payload.name, payload.category, payload.quantity, payload.unit,
                payload.expiry_date, payload.daily_usage_rate, payload.threshold,
                score, created_at,
            ),
        )
        await database.log_reorder_event(db, cursor.lastrowid, payload.quantity, payload.threshold)
        await db.commit()
        item_id = cursor.lastrowid
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cur:
            cur.row_factory = None
            row = await cur.fetchone()
            cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


@router.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item not found")
            cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


@router.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, payload: ItemUpdate):
    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item not found")
            cols = [d[0] for d in cursor.description]
        current = dict(zip(cols, row))

        updates = payload.model_dump(exclude_none=True)
        if not updates:
            return current

        for key, val in updates.items():
            current[key] = val

        current["sustainability_score"] = compute_sustainability_score(
            current["category"], current["quantity"],
            current["daily_usage_rate"], current["threshold"]
        )

        await db.execute(
            """UPDATE items SET name=?, category=?, quantity=?, unit=?, expiry_date=?,
               daily_usage_rate=?, threshold=?, sustainability_score=?
               WHERE id=?""",
            (
                current["name"], current["category"], current["quantity"], current["unit"],
                current["expiry_date"], current["daily_usage_rate"], current["threshold"],
                current["sustainability_score"], item_id,
            ),
        )
        await database.log_reorder_event(db, item_id, current["quantity"], current["threshold"])
        result = await db.execute("DELETE FROM score_explanations WHERE item_id = ?", (item_id,))
        logger.info("Cache invalidated for item %s (rows deleted: %s)", item_id, result.rowcount)
        await db.commit()
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cur:
            row = await cur.fetchone()
            cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    async with aiosqlite.connect(database.DB_PATH) as db:
        result = await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")


@router.get("/categories")
async def list_categories():
    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT DISTINCT category FROM items ORDER BY category") as cursor:
            rows = await cursor.fetchall()
    return [r[0] for r in rows]
