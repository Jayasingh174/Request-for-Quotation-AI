import os
import logging
from contextlib import asynccontextmanager # 🔥 NEW: For modern FastAPI lifecycle

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

# 🔥 NEW: Import our unified Vector Store instance!
from app.brain.vector_service import vector_store

# Configuration variables
from app.config import UPLOAD_DIR, APP_NAME, EMBEDDING_MODEL, OPENAI_API_KEY

logger = logging.getLogger(__name__)

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

    # 1️⃣ Validate OpenAI API Key
    if not OPENAI_API_KEY:
        logger.error("CRITICAL: OpenAI API Key missing from environment.")

    # 2️⃣ Ensure upload directory exists
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info(f"Directory verified: {UPLOAD_DIR}")

    # 3️⃣ Load FAISS index from disk
    try:
        # 🔥 Call the method directly on our unified class instance
        vector_store.load_index()
        logger.info("Vector index successfully restored from disk.")
    except Exception as e:
        logger.warning(f"Could not restore index: {e}. Starting fresh.")

    logger.info(f"RFQ AI System started using model: {EMBEDDING_MODEL}")
    print(f"✅ Startup Complete. Ready for Queries.\n")

    # ------------------ APP RUNS HERE ------------------
    yield 

    # ------------------ SHUTDOWN ------------------
    logger.info("Saving vector index before shutdown...")
    # 🔥 Call the method directly on our unified class instance
    vector_store.save_index()
    logger.info("Vector index saved successfully.")


# =========================================================
# 🏗️ INITIALIZE APP
# =========================================================
# Attach the lifespan manager to the app
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
app.include_router(document_router.router)  # Document viewing / management
app.include_router(upload_router.router)    # File uploads
app.include_router(query_router.router)     # RAG question answering
app.include_router(quote_router.router)     # Cost estimation / quoting
app.include_router(export_router.router)    # Export results (Excel/PDF/etc.)


# =========================================================
# 📁 STATIC FILES & FRONTEND
# =========================================================
if os.path.exists("app/web"):
    app.mount("/static", StaticFiles(directory="app/web"), name="static")
    
@app.get("/")
async def serve_frontend():
    return FileResponse("app/web/index.html")