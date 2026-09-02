import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Routers (modular API structure)
from app.routers import upload_router
from app.routers import query_router
from app.routers import quote_router
from app.routers import document_router
from app.routers import export_router

# Import our unified Vector Store instance
from app.brain.vector_service import vector_store

# Configuration variables
from app.config import UPLOAD_DIR, APP_NAME, EMBEDDING_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

# 🔧 FIX: resolve paths relative to this file's location, not the process's
# working directory — makes static/frontend serving independent of how
# and from where uvicorn is launched.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")


# =========================================================
# 🚀 LIFESPAN (Modern Startup/Shutdown)
# =========================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles system initialization and graceful shutdown cleanly.
    Everything before 'yield' runs on startup.
    Everything after 'yield' runs on shutdown.
    """
    # ------------------ STARTUP ------------------
    print(f"\n{'='*30}")
    print(f"🚀 {APP_NAME} INITIALIZING")
    print(f"{'='*30}")

    if not OPENAI_API_KEY:
        logger.error("CRITICAL: OpenAI API Key missing from environment.")

    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Directory verified: {UPLOAD_DIR}")

    # 🔧 FIX: vector_store already loads its index in __init__ at import
    # time (see app/brain/vector_service.py), so this was reading the
    # same files off disk a second time for no reason. Import alone is
    # enough — nothing modifies the store between import and here.
    logger.info(f"Vector index ready: {len(vector_store.documents)} chunks loaded.")

    logger.info(f"RFQ AI System started using model: {EMBEDDING_MODEL}")
    print(f"✅ Startup Complete. Ready for Queries.\n")

    # ------------------ APP RUNS HERE ------------------
    yield

    # ------------------ SHUTDOWN ------------------
    logger.info("Saving vector index before shutdown...")
    vector_store.save_index()
    logger.info("Vector index saved successfully.")


# =========================================================
# 🏗️ INITIALIZE APP
# =========================================================
app = FastAPI(title="RFQ AI System", lifespan=lifespan)

# =========================================================
# 🌐 CORS CONFIGURATION
# =========================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ In production, restrict this to specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# 🔌 ROUTERS (API ENDPOINTS)
# =========================================================
app.include_router(document_router.router)
app.include_router(upload_router.router)
app.include_router(query_router.router)
app.include_router(quote_router.router)
app.include_router(export_router.router)

# =========================================================
# 📁 STATIC FILES & FRONTEND
# =========================================================
if os.path.exists(WEB_DIR):
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")
else:
    # 🔧 FIX: previously failed silently — now at least visible in logs
    logger.error(f"Static directory not found at {WEB_DIR}; frontend will not be served.")


@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))
