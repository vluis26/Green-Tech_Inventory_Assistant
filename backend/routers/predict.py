import logging
from datetime import datetime, UTC

import aiosqlite
from fastapi import APIRouter, HTTPException

import database
from models import AIResponse, ScoreExplanation
from services import ai_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/items/{item_id}/predict", response_model=AIResponse)
async def predict_reorder(item_id: int):
    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item not found")
            cols = [d[0] for d in cursor.description]
    item = dict(zip(cols, row))
    return await ai_service.ai_prediction(item)


@router.get("/items/{item_id}/score-explanation", response_model=ScoreExplanation)
async def score_explanation(item_id: int):
    async with aiosqlite.connect(database.DB_PATH) as db:
        async with db.execute("SELECT * FROM items WHERE id = ?", (item_id,)) as cursor:
            row = await cursor.fetchone()
            if row is None:
                raise HTTPException(status_code=404, detail="Item not found")
            cols = [d[0] for d in cursor.description]
        item = dict(zip(cols, row))
        current_score = item["sustainability_score"]

        async with db.execute(
            "SELECT score, explanation FROM score_explanations WHERE item_id = ?", (item_id,)
        ) as cursor:
            cached = await cursor.fetchone()

        if cached and cached[0] == current_score:
            return ScoreExplanation(explanation=cached[1], source="cached", cached=True)

        source = "fallback"
        if ai_service.ANTHROPIC_API_KEY:
            try:
                explanation = await ai_service.ai_score_explanation(item)
                source = "ai"
            except Exception as e:
                logger.error("score-explanation AI call failed: %s: %s", type(e).__name__, e)
                explanation = ai_service.rule_based_explanation(item)
        else:
            explanation = ai_service.rule_based_explanation(item)

        generated_at = datetime.now(UTC).isoformat()
        await db.execute(
            """INSERT INTO score_explanations (item_id, score, explanation, generated_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(item_id) DO UPDATE SET
                 score=excluded.score,
                 explanation=excluded.explanation,
                 generated_at=excluded.generated_at""",
            (item_id, current_score, explanation, generated_at),
        )
        await db.commit()

    return ScoreExplanation(explanation=explanation, source=source, cached=False)
