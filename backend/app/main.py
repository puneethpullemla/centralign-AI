import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.db.database import init_db
from app.api.routes import tasks, executions, approvals

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("autonomous_worker")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database tables...")
    init_db()
    os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
    logger.info(f"System started with LLM Provider: {settings.effective_llm_provider}")
    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title="Autonomous AI Task Worker API",
    description="Agentic task execution system using LangGraph, Playwright browser automation, and independent verification.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(tasks.router, prefix="/api")
app.include_router(executions.router, prefix="/api")
app.include_router(approvals.router, prefix="/api")


@app.get("/api/health", tags=["Health"])
def health_check():
    """Health check endpoint for deployment orchestration and monitoring."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "llm_provider": settings.effective_llm_provider,
        "environment": settings.ENVIRONMENT
    }


# Static Mounts for Evidence Screenshots
os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
app.mount("/evidence", StaticFiles(directory=settings.EVIDENCE_DIR), name="evidence")

# Static / Direct Mounts for Sandbox Portals
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sandbox_invoices_path = os.path.join(BASE_DIR, "sandbox", "invoice-portal")
sandbox_billing_path = os.path.join(BASE_DIR, "sandbox", "billing-portal")

@app.get("/sandbox/invoice-portal", tags=["Sandbox"])
async def serve_invoice_portal():
    return FileResponse(os.path.join(sandbox_invoices_path, "index.html"))


@app.get("/sandbox/billing-portal", tags=["Sandbox"])
async def serve_billing_portal():
    return FileResponse(os.path.join(sandbox_billing_path, "index.html"))


if os.path.exists(sandbox_invoices_path):
    app.mount("/sandbox/invoice-portal/static", StaticFiles(directory=sandbox_invoices_path), name="sandbox_invoices")
if os.path.exists(sandbox_billing_path):
    app.mount("/sandbox/billing-portal/static", StaticFiles(directory=sandbox_billing_path), name="sandbox_billing")
