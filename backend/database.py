import aiosqlite
from datetime import date, datetime, UTC
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "inventory.db")


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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS score_explanations (
                item_id INTEGER PRIMARY KEY,
                score INTEGER NOT NULL,
                explanation TEXT NOT NULL,
                generated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS reorder_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_id INTEGER NOT NULL,
                triggered_at TEXT NOT NULL
            )
        """)
        await db.commit()


def row_to_dict(row, cursor) -> dict:
    cols = [d[0] for d in cursor.description]
    return dict(zip(cols, row))


async def log_reorder_event(db: aiosqlite.Connection, item_id: int, quantity: float, threshold: float):
    """Insert a reorder event for item_id if at/below threshold, deduplicated per calendar day."""
    if quantity > threshold:
        return
    today = date.today().isoformat()
    async with db.execute(
        "SELECT 1 FROM reorder_history WHERE item_id = ? AND triggered_at >= ? AND triggered_at < ?",
        (item_id, f"{today}T00:00:00", f"{today}T23:59:59"),
    ) as cur:
        if await cur.fetchone():
            return
    await db.execute(
        "INSERT INTO reorder_history (item_id, triggered_at) VALUES (?, ?)",
        (item_id, datetime.now(UTC).isoformat()),
    )
