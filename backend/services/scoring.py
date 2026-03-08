CATEGORY_BASE_SCORES = {
    "office supplies": 60,
    "food/beverage": 70,
    "cleaning": 50,
    "lab equipment": 55,
}


def compute_sustainability_score(category: str, quantity: float, daily_usage_rate: float, threshold: float) -> int:
    base = CATEGORY_BASE_SCORES.get(category.lower(), 55)
    if daily_usage_rate > 0:
        days_stock = quantity / daily_usage_rate
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
