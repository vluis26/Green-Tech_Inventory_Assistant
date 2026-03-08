import os
import sys
import logging
from contextlib import asynccontextmanager
from pathlib import Path

# Ensure backend/ is on sys.path so sibling modules (database, models, routers,
# services) are importable regardless of where uvicorn is launched from.
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env before importing any module that reads env vars at module level
_env_path = Path(__file__).parent.parent / ".env"
_loaded = load_dotenv(_env_path)
logger.info("dotenv loaded from %s: %s", _env_path, _loaded)

_api_key = os.getenv("ANTHROPIC_API_KEY", "")
logger.info(
    "ANTHROPIC_API_KEY present: %s, first 10 chars: %s",
    bool(_api_key),
    _api_key[:10] if _api_key else "MISSING",
)

# Routers and services are imported after load_dotenv so their module-level
# os.getenv() calls see the populated environment.
from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from database import init_db  # noqa: E402
from routers import items, dashboard, predict  # noqa: E402


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

app.include_router(items.router)
app.include_router(dashboard.router)
app.include_router(predict.router)
