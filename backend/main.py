from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.products import router as products_router
from routes.metrics import router as metrics_router
from routes.alerts import router as alerts_router
from routes.scraping import router as scraping_router

from database.init_db import init_db

app = FastAPI(
    title="MundoMaterno — Sistema de Inteligencia Competitiva",
    version="1.0.0"
)

# ======================================================
# CORS
# ======================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# ROUTERS
# ======================================================

app.include_router(products_router, prefix="/products", tags=["Products"])

app.include_router(metrics_router, prefix="/metrics", tags=["Metrics"])

app.include_router(alerts_router, prefix="/alerts", tags=["Alerts"])

app.include_router(scraping_router, prefix="/scraping", tags=["Scraping"])

# ======================================================
# STARTUP
# ======================================================

@app.on_event("startup")
def startup():
    print("Iniciando MundoMaterno-OpenClaw...")
    init_db()
    print("Base de datos lista.")

# ======================================================
# ROOT
# ======================================================

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "MundoMaterno backend funcionando"
    }
