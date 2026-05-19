# ==============================================================================
# ARCHIVO 1: /backend/main.py
# TIPO: Script principal de la aplicación (Python)
# FUNCIÓN: Punto de entrada del servidor FastAPI para MundoMaterno-OpenClaw.
#          Registra todos los routers, habilita CORS para que el frontend
#          React pueda consumir la API, e inicializa la base de datos SQLite
#          automáticamente al arrancar.
#
# CÓMO EJECUTAR:
#   1. Tener el entorno virtual activo (venv\Scripts\activate en Windows)
#   2. Estar dentro de la carpeta /backend
#   3. Correr: uvicorn main:app --reload
#   4. Abrir en el navegador: http://localhost:8000
#   5. Ver documentación interactiva en: http://localhost:8000/docs
# ==============================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import products, metrics, alerts, scraping
from database.init_db import init_db

# ─── Inicialización de la app ─────────────────────────────────
app = FastAPI(
    title="MundoMaterno — Sistema de Inteligencia Competitiva",
    description=(
        "API REST para monitoreo automatizado de precios y productos "
        "de competidores en el mercado de ropa materna colombiana. "
        "Competidores monitoreados: Carymar, Saraisa, OhMama."
    ),
    version="1.0.0",
    contact={
        "name": "Equipo MundoMaterno-OpenClaw",
    }
)

# ─── CORS ─────────────────────────────────────────────────────
# Sin esto, el navegador bloquea las peticiones del frontend React
# hacia esta API por política de seguridad de origen cruzado.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",   # Vite en desarrollo
        "http://localhost:3000",   # Alternativa React
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────
# Cada router agrupa los endpoints de una responsabilidad específica.
# El prefijo define la URL base de cada grupo.
app.include_router(products.router, prefix="/products", tags=["Productos"])
app.include_router(metrics.router,  prefix="/metrics",  tags=["Métricas"])
app.include_router(alerts.router,   prefix="/alerts",   tags=["Alertas"])
app.include_router(scraping.router, prefix="/scraping", tags=["Scraping"])

# ─── Evento de inicio ─────────────────────────────────────────
# Se ejecuta una vez cuando el servidor arranca.
# Crea las tablas en SQLite si todavía no existen.
@app.on_event("startup")
def on_startup():
    print("Iniciando MundoMaterno-OpenClaw...")
    init_db()
    print("Base de datos lista.")

# ─── Health check ─────────────────────────────────────────────
@app.get("/", tags=["Estado"])
def root():
    """
    Verifica que el servidor está activo.
    Primer endpoint que debes probar al levantar el backend.
    """
    return {
        "sistema": "MundoMaterno — Inteligencia Competitiva",
        "estado": "activo",
        "version": "1.0.0",
        "competidores_monitoreados": ["Carymar", "Saraisa", "OhMama"],
        "documentacion": "/docs"
    }
