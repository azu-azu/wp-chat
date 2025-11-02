import json
import os

import faiss
import joblib
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from scipy.sparse import load_npz
from sentence_transformers import SentenceTransformer

# New imports for improvements
from ..core.config import get_config_value
from ..core.exceptions import WPChatException, get_status_code
from ..core.logging_config import setup_logging
from ..management.ab_logging import ab_logging_middleware

# Load environment variables from .env file
load_dotenv()

# Initialize structured logging
logger = setup_logging(logger_name="api.chat_api")

IDX = "data/index/wp.faiss"
META = "data/index/wp.meta.json"
MODEL = "all-MiniLM-L6-v2"
TOPK_DEFAULT = get_config_value("api.topk_default", 5)
TOPK_MAX = get_config_value("api.topk_max", 10)
TFIDF_VEC = "data/index/wp.tfidf.pkl"
TFIDF_MAT = "data/index/wp.tfidf.npz"

app = FastAPI()


# Exception handler for custom exceptions
@app.exception_handler(WPChatException)
async def wpchat_exception_handler(request: Request, exc: WPChatException):
    """Handle custom WPChat exceptions"""
    return JSONResponse(status_code=get_status_code(exc), content=exc.to_dict())


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add A/B logging middleware
app.middleware("http")(ab_logging_middleware)

# Load global resources
model = SentenceTransformer(MODEL)
index = faiss.read_index(IDX)
meta = json.load(open(META, encoding="utf-8"))
tfidf_vec = joblib.load(TFIDF_VEC) if os.path.exists(TFIDF_VEC) else None
tfidf_mat = load_npz(TFIDF_MAT) if os.path.exists(TFIDF_MAT) else None

# Import and configure routers (after globals initialized)
from .routers import admin_backup, admin_cache, admin_canary, admin_incidents  # noqa: E402
from .routers import chat as chat_router  # noqa: E402
from .routers import stats as stats_router  # noqa: E402

chat_router.init_globals(model, index, meta, tfidf_vec, tfidf_mat, TOPK_DEFAULT, TOPK_MAX)
app.include_router(chat_router.router, tags=["Chat"])
app.include_router(stats_router.router, prefix="/stats", tags=["Stats"])
app.include_router(admin_canary.router, prefix="/admin/canary", tags=["Admin-Canary"])
app.include_router(admin_incidents.router, prefix="/admin/incidents", tags=["Admin-Incidents"])
app.include_router(admin_backup.router, prefix="/admin/backup", tags=["Admin-Backup"])
app.include_router(admin_cache.router, prefix="/admin/cache", tags=["Admin-Cache"])


# Dashboard HTML endpoint
@app.get("/dashboard")
def serve_dashboard():
    """Serve the dashboard HTML page"""
    try:
        with open("dashboard.html", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        return JSONResponse({"error": "Dashboard file not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
