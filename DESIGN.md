# Green-Tech Inventory Assistant — Design Document

---

## 1. Problem Statement

Small businesses, non-profits, and institutional labs share a common operational blind spot: **inventory waste**. Without dedicated procurement staff or enterprise ERP systems, these organizations routinely over-order perishable supplies, miss expiry windows, and run stockouts that interrupt operations. The consequences compound quickly:

- **Food waste** in small cafes and university canteens contributes to unnecessary carbon emissions and disposal costs.
- **Lab reagent waste** at university and research labs results in costly disposal of hazardous materials and budget overruns on tight grants.
- **Office supply hoarding** ties up capital in excess stock and generates landfill waste when items are eventually discarded.
- **Reactive reordering** — placing orders only after a stockout — disrupts service continuity and often leads to emergency purchases at premium prices.

Enterprise inventory platforms (SAP, NetSuite, Oracle) solve these problems but are priced and scoped for large organizations. The gap in the market is a **lightweight, AI-assisted tool** that gives small teams the intelligence of a procurement manager without the overhead of an enterprise platform.

---

## 2. Solution Overview

The Green-Tech Inventory Assistant is a web application designed for **small businesses, non-profits, independent cafes, and university research labs**. It provides proactive inventory management with a sustainability lens — surfacing not just what is running low, but which items carry the highest waste risk and what greener alternatives exist.

**Core capabilities:**

| Feature | What it does |
|---|---|
| Inventory CRUD | Track items with quantity, usage rate, expiry date, and reorder threshold |
| Dashboard | At-a-glance view of low-stock items and inventory expiring within 7 days |
| AI Reorder Predictions | Predict days until reorder and suggest sustainable alternatives per item |
| Sustainability Score | 0–100 score per item based on category and stock efficiency |
| Score Explanation | AI-generated, cached explanation of what drives each item's score |
| Quick Add (NLP) | Describe an item in plain English and auto-fill the form fields |
| CSV Import | Bulk-load inventory from a spreadsheet |
| Waste Savings Summary | Monthly count of items flagged before stockout |

**Target users:**

- **Non-profits** running food pantries or community kitchens tracking perishable donations
- **Small cafes** managing ingredients, packaging, and cleaning supplies across one or two locations
- **University labs** monitoring reagents, consumables, and shared equipment

---

## 3. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Browser                              │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              React 19 + Vite + Tailwind CSS          │   │
│  │                                                     │   │
│  │  ┌──────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │Dashboard │  │InventoryTable│  │  ItemModal   │  │   │
│  │  └──────────┘  └──────────────┘  │  (Quick Add) │  │   │
│  │  ┌────────────┐ ┌─────────────┐  └──────────────┘  │   │
│  │  │ScoreBadge  │ │PredictPanel │                     │   │
│  │  │(popover)   │ │             │                     │   │
│  │  └────────────┘ └─────────────┘                     │   │
│  └───────────────────────┬─────────────────────────────┘   │
│                          │  HTTP (Vite proxy → :8000)       │
└──────────────────────────┼──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   FastAPI Backend (:8000)                    │
│                                                             │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │routers/     │  │routers/      │  │routers/           │  │
│  │items.py     │  │dashboard.py  │  │predict.py         │  │
│  │             │  │              │  │                   │  │
│  │ CRUD        │  │ /dashboard   │  │ /predict          │  │
│  │ /import     │  │ /waste-      │  │ /score-           │  │
│  │ /parse-desc │  │  savings     │  │  explanation      │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                │                    │             │
│  ┌──────▼────────────────▼────────────────────▼──────────┐  │
│  │                   services/                           │  │
│  │  ┌─────────────────────────┐  ┌────────────────────┐  │  │
│  │  │    ai_service.py        │  │    scoring.py      │  │  │
│  │  │  ai_prediction()        │  │  compute_score()   │  │  │
│  │  │  ai_score_explanation() │  └────────────────────┘  │  │
│  │  │  parse_description_ai() │                          │  │
│  │  │  rule_based_*() fallback│                          │  │
│  │  └────────────┬────────────┘                          │  │
│  └───────────────┼───────────────────────────────────────┘  │
│                  │                                          │
│  ┌───────────────▼───────────────────────────────────────┐  │
│  │                   database.py                         │  │
│  │   init_db()  /  log_reorder_event()  /  DB_PATH       │  │
│  └───────────────────────────┬───────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────┘
                               │
          ┌────────────────────┼──────────────────────┐
          │                    │                      │
┌─────────▼──────────┐         │             ┌────────▼────────┐
│   SQLite DB        │         │             │  Anthropic API  │
│   inventory.db     │         │             │  claude-haiku-  │
│                    │         │             │  4-5-20251001   │
│  items             │         │             │                 │
│  score_explanations│         │             │  /v1/messages   │
│  reorder_history   │         │             └─────────────────┘
└────────────────────┘         │
                       (only on predict,
                        score-explanation,
                        and parse-description
                        endpoints)
```

---

## 4. Key Design Decisions

### Why FastAPI over Flask

FastAPI was chosen over Flask for one primary reason: **native async/await support**. Every call to the Anthropic API is a network-bound operation that can take 1–4 seconds. In a synchronous Flask application, that request would block the entire server thread, making the app unresponsive to other users during AI calls. FastAPI runs on an async event loop (via Uvicorn/asyncio), so AI calls, database queries, and other requests can all be interleaved without blocking.

Secondary benefits of FastAPI: automatic OpenAPI docs at `/docs`, built-in request validation via Pydantic, and first-class support for file uploads (`UploadFile`) used by the CSV import endpoint — all without additional libraries.

### Why SQLite over PostgreSQL

SQLite was chosen deliberately for this prototype stage:

- **Zero setup** — no database server to install, configure, or manage. The DB is a single file (`backend/inventory.db`) that travels with the project.
- **Sufficient for single-user scope** — a small business or non-profit running this tool has one or two concurrent users, far below SQLite's write-concurrency ceiling.
- **Async compatibility** — `aiosqlite` wraps SQLite in a thread pool, providing non-blocking access that fits the FastAPI async model.
- **Easy reset** — during development and demos, the entire database can be wiped by deleting one file.

The limitation is clear: SQLite does not support concurrent writes from multiple processes, making it unsuitable for multi-location deployments or horizontal scaling. When the product outgrows a single instance, migration to PostgreSQL (with asyncpg or SQLAlchemy async) would be the natural next step, requiring only changes to `database.py`.

### Why a Rule-Based Fallback Exists

Three conditions can prevent an Anthropic API call from succeeding:

1. **No API key configured** — the `.env` file is missing or the key is not set. This is common during first-run setup and development.
2. **Insufficient account credits** — the API key is valid but the account balance is depleted (the exact error encountered during development of this project).
3. **Network or API outage** — transient failures that should not crash the user-facing feature.

In all three cases, the fallback computes deterministic results from the item's own data:
- **Reorder date** = `(quantity - threshold) / daily_usage_rate` days from today
- **Sustainable alternatives** = a static lookup table keyed by category
- **Score explanation** = a template string filled with the actual days-of-stock figure and category baseline

The fallback ensures the application is **fully functional without any API key**, which matters for non-profits with tight budgets who may trial the tool before committing to AI costs.

### Why the Sustainability Score Uses Static Weights

The current scoring formula is:

```
score = category_base_score + efficiency_bonus(days_of_stock)
```

Where category base scores (e.g. `food/beverage = 70`, `cleaning = 50`) and efficiency bonus thresholds (≤30 days = +20, 31–60 days = +10, >60 days = +0) are **hardcoded constants**.

**Why static weights were chosen for this version:**

- **No ground truth data** — calculating a meaningful sustainability score requires supply chain data (transport emissions, packaging material, end-of-life disposal) that is not available at item-creation time without integration to external databases.
- **Interpretability** — static weights produce scores that users can understand and predict. A dynamic ML model would be a black box, making the score feel arbitrary and eroding trust.
- **Speed of implementation** — getting a working, explainable score in front of users quickly allows validation of whether the feature is useful before investing in data sourcing.

**Known limitation:** The category weights are not grounded in real lifecycle analysis data. A `food/beverage` item does not inherently have a higher sustainability potential than a `cleaning` item — it depends on specific products, sourcing, and packaging.

**Future improvement path:** Integrate a product database (e.g. Open Food Facts, GoodGuide, or a supplier sustainability API) to replace category-level weights with product-specific scores. The `compute_sustainability_score` function in `services/scoring.py` is intentionally isolated so this replacement can be made without touching any other module.

### Why `daily_usage_rate` Is Manually Entered

The daily usage rate is the most important input to the reorder prediction — it determines days of stock remaining and when to reorder. A fully automated system would learn this from historical transaction data (e.g. recording every time an item is consumed or restocked).

Manual entry was chosen as a **deliberate scoping decision** for this prototype:

- **No transaction log UI exists** — building a "record consumption" workflow would double the surface area of the MVP and delay validation of the core value proposition.
- **Users often already know their usage** — a cafe knows it uses roughly 2kg of coffee per week; a lab knows it runs 80 pipette tips per day. Manual entry is faster than teaching the system over weeks of observation.
- **Data quality is higher** — learned rates from sparse early data are noisy and can produce wildly incorrect reorder predictions that undermine trust in the tool.

The architecture accommodates the future addition of learned rates: a `consumption_log` table could be added to `database.py`, and `daily_usage_rate` could be auto-populated from rolling averages without changing any route signatures.

---

## 5. AI Integration Details

Three endpoints make calls to the Anthropic API using `claude-haiku-4-5-20251001`. Haiku was chosen over Sonnet or Opus for this use case because the tasks are structured extraction and short-form generation — Haiku's speed and cost profile are well suited, and latency matters in an interactive UI.

### `GET /items/{id}/predict`

**What the prompt does:** Given an item's name, category, quantity, daily usage rate, threshold, and expiry date, asks the model to return a JSON object with `days_until_reorder`, `reorder_date`, a list of 1–2 `sustainable_alternatives`, and a short `reasoning` string.

**Prompt constraints:** The model is explicitly told to respond with raw JSON only (no markdown fences). A post-processing step strips code fences if the model ignores this instruction.

**Fallback trigger:** Any exception — including `BadRequestError` (insufficient credits), `AuthenticationError`, network timeout, or JSON parse failure — falls back to the rule-based calculation.

### `GET /items/{id}/score-explanation`

**What the prompt does:** Given an item's sustainability score and the full scoring formula (category base + days-of-stock efficiency bonus), asks the model to write exactly 2 sentences: one explaining what drives the current score, one giving a concrete improvement suggestion. The prompt explicitly states that changing the reorder threshold does not affect the score, preventing the model from giving incorrect advice.

**Caching:** Explanations are stored in the `score_explanations` table keyed by `(item_id, score)`. A cached entry is returned immediately without an API call if the item's current score matches the cached score. The cache is invalidated (deleted) whenever `PUT /items/{id}` is called, ensuring the explanation always reflects the item's current state.

**Fallback:** A template-based string is generated from the days-of-stock value and category, producing the same two-sentence structure without an API call.

### `POST /items/parse-description`

**What the prompt does:** Accepts a free-text description (e.g. "50 coffee bags, expires June 2026, we use about 2 per day") and asks the model to extract structured fields: `name`, `category`, `quantity`, `unit`, `expiry_date`, `daily_usage_rate`, `threshold`. The prompt includes rules for date normalization (vague months → last day of month) and threshold defaulting (20% of quantity if not stated).

**No fallback:** This endpoint requires the AI — there is no rule-based way to parse arbitrary natural language into structured fields. If the API key is missing the endpoint returns HTTP 503; if the key is present but the AI call fails, it returns HTTP 502. In either case the user falls back to filling the form manually.

---

## 6. Future Enhancements

**Proactive reorder notifications with location awareness**
Currently the dashboard must be visited to see alerts. A background scheduler (e.g. APScheduler or Celery beat) could check stock levels nightly and send email or push notifications when items approach their threshold. Location-aware enhancements could suggest nearby sustainable suppliers based on the user's city, reducing last-mile transport emissions.

**Usage history learning**
Replace manually entered `daily_usage_rate` with learned rates derived from a `consumption_log` table. Users would log each time they consume or restock an item; a rolling 30-day average would replace the static rate. Seasonal patterns (e.g. a cafe using more oat milk in winter) could be modelled with simple time-series smoothing.

**Supplier directory API integration**
Connect to a sustainable supplier database (e.g. EcoVadis, B Corp directory, or a regional green procurement API) so that AI alternative suggestions link directly to verified sustainable vendors, including pricing and lead time data.

**Photo shelf scanning via Claude's vision API**
Allow users to photograph a storage shelf or stockroom. Claude's vision capabilities could identify items, read labels, and estimate quantities — pre-populating the inventory form without any manual entry. This would dramatically lower the friction of initial setup and routine stock checks.

**Multi-location and multi-user support**
Add user authentication (OAuth2 / JWT) and a `locations` table so small businesses with multiple sites can manage inventory centrally while viewing per-location dashboards. SQLite would be migrated to PostgreSQL at this point to support concurrent writes.

**Carbon footprint tracking per item**
Extend the sustainability score to include estimated CO₂ per unit sourced, using product-level emissions data from APIs such as Climatiq or supplier carbon disclosure reports. The score would evolve from a proxy metric to a real lifecycle-informed number.

---

## 7. Security Considerations

**API key handling**
The Anthropic API key is loaded exclusively from a `.env` file via `python-dotenv`. The `.env` file is not committed to version control (it should be listed in `.gitignore`). A `.env.example` with a placeholder value is provided as a template. The key is read once at application startup and stored in the `ANTHROPIC_API_KEY` module-level variable in `services/ai_service.py`; it is never logged in full, never returned in any API response, and never written to the database.

**No real user data**
This prototype does not collect or store any personally identifiable information. There are no user accounts, no authentication tokens, and no session data. The only persistent data is the inventory items entered by the operator — product names, quantities, and usage rates — which are not sensitive.

**Synthetic dataset only**
The `sample_data.json` and `sample_import_template.csv` files contain entirely fictional inventory items created for demonstration purposes. No real business data, customer records, or supplier contracts are included in the repository.

**CORS configuration**
The FastAPI app currently sets `allow_origins=["*"]` for development convenience, permitting requests from any origin. Before any production deployment, this should be restricted to the specific frontend domain to prevent cross-origin abuse of the API endpoints.

**Future hardening**
A production deployment would additionally require: HTTPS termination, rate limiting on the AI endpoints (to prevent cost amplification attacks), input sanitisation on the CSV import (to guard against formula injection in downstream spreadsheet exports), and authentication middleware before any multi-user rollout.
