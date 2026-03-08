import os
import json
import logging
from datetime import date, timedelta

from models import AIResponse

logger = logging.getLogger(__name__)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

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
        days_until_reorder = max(0, int((qty - threshold) / usage))
        reorder_date = (date.today() + timedelta(days=days_until_reorder)).isoformat()
    else:
        days_until_reorder = None
        reorder_date = None

    alternatives = SUSTAINABLE_ALTERNATIVES.get(
        category, ["generic eco-certified substitute", "bulk-purchase option"]
    )

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


def rule_based_explanation(item: dict) -> str:
    score = item["sustainability_score"]
    category = item["category"].lower()
    qty = item["quantity"]
    usage = item["daily_usage_rate"]

    if usage > 0:
        days_stock = qty / usage
        if days_stock > 60:
            stock_note = f"you're holding {int(days_stock)} days of stock, which risks waste before use."
            suggestion = "Reduce order quantities to keep 14–30 days of supply on hand."
        elif days_stock > 30:
            stock_note = f"your stock covers {int(days_stock)} days, slightly above the ideal 30-day window."
            suggestion = "Trim your next order by 20–30% to tighten the supply cycle."
        else:
            stock_note = f"your {int(days_stock)}-day supply level is efficient."
            suggestion = "Explore certified-sustainable suppliers to push the score above 90."
    else:
        stock_note = "no daily usage rate is set, so efficiency can't be calculated."
        suggestion = "Add a daily usage rate so the system can optimise your reorder cycle."

    base_scores = {"office supplies": 60, "food/beverage": 70, "cleaning": 50, "lab equipment": 55}
    base = base_scores.get(category, 55)
    category_note = f"The {category} category starts with a base score of {base}/100"

    return (
        f"Score {score}/100: {category_note}, and {stock_note} "
        f"Suggestion: {suggestion}"
    )


async def ai_score_explanation(item: dict) -> str:
    import anthropic

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    usage = item["daily_usage_rate"]
    days_stock = round(item["quantity"] / usage, 1) if usage > 0 else None

    prompt = f"""You are a sustainability expert advising a small business on inventory practices.

Item: {item['name']} ({item['category']})
Sustainability score: {item['sustainability_score']}/100
Current stock: {item['quantity']} {item['unit']}
Daily usage: {usage} {item['unit']}/day
Days of stock on hand: {days_stock if days_stock is not None else 'unknown'}
Reorder threshold: {item['threshold']} {item['unit']}

HOW THE SCORE IS CALCULATED:
- Base score comes from category: office supplies=60, food/beverage=70, cleaning=50, lab equipment=55
- Efficiency bonus is added based on days of stock on hand (quantity / daily_usage_rate):
  * 0-30 days of stock → +20 bonus (ideal, minimises waste risk)
  * 31-60 days of stock → +10 bonus (slightly overstocked)
  * >60 days of stock → +0 bonus (overstocked, high waste risk)
- The ONLY way to improve the score is to reduce days of stock on hand.
- Changing the reorder threshold does NOT affect the score.

Write exactly 2 sentences:
1. Explain what is driving this score using the actual days-of-stock figure and category baseline.
2. Give one concrete suggestion — either reduce the current quantity on hand or reorder more frequently in smaller batches to keep days of stock in the 0-30 day range.

No bullet points, no headers, no markdown. Just the 2 sentences."""

    message = await client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=150,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


async def parse_description_ai(description: str) -> dict:
    import anthropic

    if not ANTHROPIC_API_KEY:
        raise ValueError("Anthropic API key not configured")

    client = anthropic.AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""Extract inventory item fields from this natural language description.

Description: "{description}"

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
    return json.loads(raw)
