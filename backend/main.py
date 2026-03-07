import os
import math
import json
from datetime import date, datetime, timedelta, UTC
from typing import Optional, List
from contextlib import asynccontextmanager

import logging

import aiosqlite
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_env_path = Path(__file__).parent.parent / ".env"
_loaded = load_dotenv(_env_path)
logger.info("dotenv loaded from %s: %s", _env_path, _loaded)

DB_PATH = str(Path(__file__).parent / "inventory.db")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
logger.info("ANTHROPIC_API_KEY present: %s, first 10 chars: %s", bool(ANTHROPIC_API_KEY), ANTHROPIC_API_KEY[:10] if ANTHROPIC_API_KEY else "MISSING")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class ItemCreate(BaseModel):
    name: str
    category: str
    quantity: float
    unit: str
    expiry_date: Optional[str] = None          # ISO date string or None
    daily_usage_rate: float = Field(ge=0)
    threshold: float = Field(ge=0)


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[str] = None
    daily_usage_rate: Optional[float] = None
    threshold: Optional[float] = None


class Item(ItemCreate):
    id: int
    sustainability_score: int
    created_at: str

    class Config:
        from_attributes = True


class AIResponse(BaseModel):
    days_until_reorder: Optional[int]
    reorder_date: Optional[str]
    sustainable_alternatives: List[str]
    reasoning: str
    source: str  # "ai" or "fallback"


# ---------------------------------------------------------------------------
# Sustainability scoring
# ---------------------------------------------------------------------------

CATEGORY_BASE_SCORES = {
    "office supplies": 60,
    "food/beverage": 70,
    "cleaning": 50,
    "lab equipment": 55,
}

def compute_sustainability_score(category: str, quantity: float, daily_usage_rate: float, threshold: float) -> int:
    base = CATEGORY_BASE_SCORES.get(category.lower(), 55)
    # Efficiency bonus: lower overstocking ratio = more sustainable
    if daily_usage_rate > 0:
        days_stock = quantity / daily_usage_rate
        # Ideal: 7-30 days of stock. Penalty for >60 days (hoarding waste).
        if days_stock <= 30:
            efficiency_bonus = 20
        elif days_stock <= 60:
            efficiency_bonus = 10
        else:
            efficiency_bonus = 0
    else:
        efficiency_bonus = 10  # unknown usage, neutral
    score = base + efficiency_bonus
    return min(100, max(0, score))


# ---------------------------------------------------------------------------
# Rule-based fallback
# ---------------------------------------------------------------------------

SUSTAINABLE_ALTERNATIVES = {
    "office supplies": ["recycled-content paper products", "refillable ink cartridges"],
    "food/beverage": ["locally sourced organic alternatives", "bulk-bin unpackaged goods"],
    "cleaning": ["concentrated eco-certified cleaners", "reusable microfibre cloth kits"],
    "lab equipment": ["refurbished certified lab instruments", "shared-use equipment program"],
}

def rule_based_prediction(item: dict) -> AIResponse:
    qty = item["quantity"]
    usage = item["daily_usage_rate"]
    threshold = item["threshold"]
    category = item.get("category", "").lower()

    if usage > 0:
        days_remaining = qty / usage
        days_until_reorder = max(0, int((qty - threshold) / usage))
        reorder_date = (date.today() + timedelta(days=days_until_reorder)).isoformat()
    else:
        days_until_reorder = None
        reorder_date = None

    alternatives = SUSTAINABLE_ALTERNATIVES.get(category, ["generic eco-certified substitute", "bulk-purchase option"])

    return AIResponse(
        days_until_reorder=days_until_reorder,
        reorder_date=reorder_date,
        sustainable_alternatives=alternatives,
        reasoning=(
            f"Fallback calculation: {qty} {item['unit']} at {usage}/day. "
            f"Reorder when stock hits threshold ({threshold})."
        ),
        source="fallback",
    )


# ---------------------------------------------------------------------------
# AI prediction via Anthropic
# ---------------------------------------------------------------------------

async def ai_prediction(item: dict) -> AIResponse:
    if not ANTHROPIC_API_KEY:
        return rule_based_prediction(item)

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

        prompt = f"""You are a sustainability-focused inventory assistant for small businesses and non-profits.

Given this inventory item:
- Name: {item['name']}
- Category: {item['category']}
- Current quantity: {item['quantity']} {item['unit']}
- Daily usage rate: {item['daily_usage_rate']} {item['unit']}/day
- Reorder threshold: {item['threshold']} {item['unit']}
- Expiry date: {item.get('expiry_date') or 'N/A'}

Respond ONLY with a JSON object (no markdown, no extra text) with these keys:
{{
  "days_until_reorder": <integer or null>,
  "reorder_date": "<YYYY-MM-DD or null>",
  "sustainable_alternatives": ["<alt 1>", "<alt 2>"],
  "reasoning": "<1-2 sentence explanation>"
}}

Today is {date.today().isoformat()}.
Base days_until_reorder on when stock will hit the threshold at the current usage rate.
Suggest 1-2 realistic sustainable alternatives appropriate for a {item['category']} item."""

        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()
        # Strip markdown code fences if the model wraps the JSON in ```json ... ```
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)

        return AIResponse(
            days_until_reorder=data.get("days_until_reorder"),
            reorder_date=data.get("reorder_date"),
            sustainable_alternatives=data.get("sustainable_alternatives", []),
            reasoning=data.get("reasoning", ""),
            source="ai",
        )

    except Exception as e:
        logger.error("Anthropic API call failed: %s: %s", type(e).__name__, e)
        return rule_based_prediction(item)


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

async def get_db():
    return await aiosqlite.connect(DB_PATH)


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                quantity REAL NOT NULL,
                unit TEXT NOT NULL,
                expiry_date TEXT,
                daily_usage_rate REAL NOT NULL DEFAULT 0,
                threshold REAL NOT NULL DEFAULT 0,
                sustainability_score INTEGER NOT NULL DEFAULT 50,
                created_at TEXT NOT NULL
            )
        """)
        await db.commit()


def row_to_dict(row, cursor) -> dict:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Green-Tech Inventory Assistant", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routes - CRUD
# ---------------------------------------------------------------------------

@app.get("/items", response_model=List[Item])
async def list_items(
    search: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    async with aiosqlite.connect(DB_PATH) as db:
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


@app.post("/items", response_model=Item, status_code=201)
async def create_item(payload: ItemCreate):
    score = compute_sustainability_score(
        payload.category, payload.quantity, payload.daily_usage_rate, payload.threshold
    )
    created_at = datetime.now(UTC).isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
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
        await db.commit()
        item_id = cursor.lastrowid
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cur:
            cur.row_factory = None
            row = await cur.fetchone()
            cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item not found")
            cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, payload: ItemUpdate):
    async with aiosqlite.connect(DB_PATH) as db:
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
        await db.commit()
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cur:
            row = await cur.fetchone()
            cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


@app.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        result = await db.execute("DELETE FROM items WHERE id = ?", (item_id,))
        await db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Item not found")


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@app.get("/dashboard")
async def dashboard():
    today = date.today()
    week_ahead = today + timedelta(days=7)

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        async with db.execute("SELECT * FROM items") as cursor:
            all_items = [dict(r) for r in await cursor.fetchall()]

    low_stock = []
    expiring_soon = []

    for item in all_items:
        if item["quantity"] <= item["threshold"]:
            low_stock.append(item)
        if item["expiry_date"]:
            try:
                exp = date.fromisoformat(item["expiry_date"])
                if today <= exp <= week_ahead:
                    expiring_soon.append(item)
            except ValueError:
                pass

    avg_score = (
        round(sum(i["sustainability_score"] for i in all_items) / len(all_items))
        if all_items else 0
    )

    return {
        "total_items": len(all_items),
        "low_stock": low_stock,
        "expiring_soon": expiring_soon,
        "average_sustainability_score": avg_score,
    }


# ---------------------------------------------------------------------------
# AI endpoint
# ---------------------------------------------------------------------------

@app.get("/items/{item_id}/predict", response_model=AIResponse)
async def predict_reorder(item_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item not found")
            cols = [d[0] for d in cursor.description]
    item = dict(zip(cols, row))
    return await ai_prediction(item)


# ---------------------------------------------------------------------------
# Parse natural-language description into item fields
# ---------------------------------------------------------------------------

class ParseRequest(BaseModel):
    description: str


class ParsedItem(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[str] = None
    daily_usage_rate: Optional[float] = None
    threshold: Optional[float] = None


@app.post("/items/parse-description", response_model=ParsedItem)
async def parse_description(payload: ParseRequest):
    if not ANTHROPIC_API_KEY:
        raise HTTPException(status_code=503, detail="Anthropic API key not configured")

    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Extract inventory item fields from this natural language description.

Description: "{payload.description}"

Respond ONLY with a JSON object (no markdown, no extra text) with these keys (omit any you cannot determine):
{{
  "name": "<item name>",
  "category": "<one of: office supplies, food/beverage, cleaning, lab equipment>",
  "quantity": <number>,
  "unit": "<unit of measure, e.g. bags, bottles, sheets>",
  "expiry_date": "<YYYY-MM-DD or null>",
  "daily_usage_rate": <number or null>,
  "threshold": <number or null>
}}

Rules:
- Infer category from the item type if not stated
- Convert vague expiry like "June 2026" to the last day of that month: "2026-06-30"
- If threshold is not mentioned, set it to roughly 20% of quantity
- Today is {date.today().isoformat()}"""

    try:
        message = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        data = json.loads(raw)
        return ParsedItem(**{k: v for k, v in data.items() if v is not None})
    except Exception as e:
        logger.error("parse-description failed: %s: %s", type(e).__name__, e)
        raise HTTPException(status_code=502, detail=f"AI parsing failed: {e}")


# ---------------------------------------------------------------------------
# Categories
# ---------------------------------------------------------------------------

@app.get("/categories")
async def list_categories():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT DISTINCT category FROM items ORDER BY category") as cursor:
            rows = await cursor.fetchall()
    return [r[0] for r in rows]
