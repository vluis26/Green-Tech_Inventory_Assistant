# Green-Tech Inventory Assistant

A web app for small businesses and non-profits to manage inventory sustainably — reducing waste through smart reorder predictions and eco-friendly alternative suggestions.

---

## Submission Info

- **Candidate Name:** Luis Villa
- **Scenario Chosen:** Green-Tech Inventory Assistant
- **Estimated Time Spent:** 5 Hours
- **YouTube Link:** https://youtu.be/_9GWGrhIw5s

## Getting Started

**Prerequisites:** Python 3.12+, Node.js 18+, Anthropic API key (console.anthropic.com)

### 1. Clone & configure environment

```bash
git clone https://github.com/vluis26/Green-Tech_Inventory_Assistant
cd Green-Tech_Inventory_Assistant
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 2. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`. Interactive docs: `http://localhost:8000/docs`.

### 3. Load sample data

```bash
# From the project root, with the backend running:
python - <<'EOF'
import json, urllib.request, urllib.parse

with open("sample_data.json") as f:
    items = json.load(f)

for item in items:
    data = json.dumps(item).encode()
    req = urllib.request.Request(
        "http://localhost:8000/items",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    urllib.request.urlopen(req)
    print(f"Added: {item['name']}")
EOF
```

### 4. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

**AI Disclosure:**
- Did you use an AI assistant? Yes — Claude Code for scaffolding and debugging
- How did you verify suggestions? Ran the app end-to-end, tested all CRUD operations, verified AI and fallback prediction outputs, confirmed 2/2 pytest tests passing
- One example of a suggestion I rejected or changed: Claude Code initially scaffolded the entire backend as a single 767-line main.py file. I rejected this and directed it to refactor into a proper module structure (routers/, services/, database.py, models.py) with clear separation of concerns. I also rejected the AI's suggestion to call the Anthropic API on every score badge click — instead I implemented a SQLite-backed cache that stores explanations by item_id and score, only re-calling the API when the score actually changes.

**Tradeoffs & Prioritization:**
- What I cut to stay within time: (1) Usage history logging — predictions use a manually entered daily_usage_rate as a proxy rather than learned consumption patterns. A production version would log every quantity update and feed that history to the AI for more accurate forecasting. (2) AI-powered sustainability scoring — the current score uses static category weights. Ideally Claude would score each item by name and sourcing using real supply chain data. (3) Proactive reorder notifications with local supplier recommendations — intentionally excluded because without user location data, 'local supplier' suggestions would be fabricated. The right implementation requires location consent + a verified supplier directory API.
- What I'd build next: Visual shelf scanning via Claude's vision API, automated supplier email integration, carbon footprint tracking per item(similar to Chipotle)
- Known limitations: Sustainability score uses static category weights rather than real supply chain data; AI suggestions are general rather than hyperlocal; daily_usage_rate is manually entered rather than learned from history

---


## Features

- **Inventory CRUD** — create, read, update, and delete items with name, category, quantity, unit, expiry date, daily usage rate, and reorder threshold
- **Search & Filter** — filter by category or search by name in real time
- **Quick Add (NLP)** — describe an item in plain English and auto-fill the form fields via AI
- **CSV Import** — bulk-load inventory from a spreadsheet using the provided template
- **AI Reorder Predictions** — powered by Claude (`claude-haiku-4-5-20251001`) to predict days until reorder and suggest sustainable alternatives; rule-based fallback when the API is unavailable
- **Dashboard** — at-a-glance view of low-stock items and inventory expiring within 7 days
- **Waste Savings Summary** — monthly count of items flagged before stockout and most-at-risk item
- **Sustainability Score** — 0–100 score per item based on category and usage efficiency
- **Score Explanation** — AI-generated, cached explanation of what drives each item's score with improvement suggestions
- **Sample Data** — 15 realistic items across four categories ready to load

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + aiosqlite (Python) |
| Frontend | React 19 + Vite + Tailwind CSS v4 |
| AI | Anthropic API (`claude-haiku-4-5-20251001`) |
| Tests | pytest + pytest-asyncio + httpx |

---

## Project Structure

```
Green-Tech_Inventory_Assistant/
├── backend/
│   ├── main.py            # FastAPI app setup, lifespan, CORS, route registration
│   ├── database.py        # DB connection, init, helpers
│   ├── models.py          # Pydantic request/response models
│   ├── routers/
│   │   ├── items.py       # CRUD endpoints
│   │   ├── dashboard.py   # Dashboard + waste savings endpoints
│   │   └── predict.py     # AI prediction + score explanation endpoints
│   ├── services/
│   │   ├── ai_service.py  # Anthropic API calls and fallback logic
│   │   └── scoring.py     # Sustainability score computation
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       └── components/
│           ├── Dashboard.jsx
│           ├── InventoryTable.jsx
│           ├── ItemModal.jsx
│           ├── PredictPanel.jsx
│           └── ScoreBadge.jsx
├── tests/
│   ├── test_inventory.py
│   └── requirements-test.txt
├── sample_data.json
├── .env.example
└── README.md
```

---

## API Reference

| Method | Path | Description |
|--------|------|-------------|
| GET | `/items` | List items (optional `?search=` & `?category=`) |
| POST | `/items` | Create item |
| GET | `/items/{id}` | Get single item |
| PUT | `/items/{id}` | Update item |
| DELETE | `/items/{id}` | Delete item |
| GET | `/items/{id}/predict` | AI reorder prediction |
| GET | `/items/{id}/score-explanation` | AI-generated sustainability score explanation (cached) |
| POST | `/items/import` | Bulk import items from CSV file |
| POST | `/items/parse-description` | Parse plain-English description into item fields (AI) |
| GET | `/dashboard` | Low-stock + expiring summary |
| GET | `/dashboard/waste-savings` | Monthly reorder event stats |
| GET | `/categories` | List distinct categories |

---

## Running Tests

```bash
# From the project root
pip install -r tests/requirements-test.txt -r backend/requirements.txt
pytest tests/ -v
```

---

## Sustainability Score

Each item receives a 0–100 score computed at save time:

| Factor | Detail |
|--------|--------|
| Category base | office supplies 60, food/beverage 70, cleaning 50, lab equipment 55 |
| Efficiency bonus | +20 if ≤30 days of stock, +10 if 31-60 days, +0 if >60 days |

---

## AI Fallback

If the Anthropic API is unavailable or the key is missing, the `/predict` endpoint falls back to:

- **Days until reorder** = `(quantity − threshold) / daily_usage_rate`
- **Alternatives** = a curated static list per category
