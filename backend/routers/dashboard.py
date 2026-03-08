import aiosqlite
from datetime import date, timedelta
from fastapi import APIRouter

import database

router = APIRouter()


@router.get("/dashboard")
async def dashboard():
    today = date.today()
    week_ahead = today + timedelta(days=7)

    async with aiosqlite.connect(database.DB_PATH) as db:
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


@router.get("/dashboard/waste-savings")
async def waste_savings():
    today = date.today()
    month_start = today.replace(day=1).isoformat()

    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute(
            "SELECT COUNT(DISTINCT item_id) FROM reorder_history WHERE triggered_at >= ?",
            (f"{month_start}T00:00:00",),
        ) as cur:
            items_reordered_this_month = (await cur.fetchone())[0]

        async with db.execute(
            "SELECT COUNT(*) FROM reorder_history WHERE triggered_at >= ?",
            (f"{month_start}T00:00:00",),
        ) as cur:
            total_reorder_events = (await cur.fetchone())[0]

        async with db.execute(
            """SELECT rh.item_id, i.name, COUNT(*) as cnt
               FROM reorder_history rh
               LEFT JOIN items i ON i.id = rh.item_id
               GROUP BY rh.item_id
               ORDER BY cnt DESC
               LIMIT 1""",
        ) as cur:
            row = await cur.fetchone()
            most_at_risk = {"name": row[1], "count": row[2]} if row else None

    return {
        "items_reordered_this_month": items_reordered_this_month,
        "total_reorder_events": total_reorder_events,
        "most_at_risk_item": most_at_risk,
    }
