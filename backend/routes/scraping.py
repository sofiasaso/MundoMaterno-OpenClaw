# ==============================================================================
# ARCHIVO 9: /backend/routes/scraping.py
# TIPO: Router / Controlador API (Python)
# FUNCIÓN: Expone los endpoints HTTP que disparan la ejecución del scraping
#          y consultan el estado del sistema. Este archivo es la PUERTA DE
#          ENTRADA, no hace el scraping directamente.
#
# DIFERENCIA CON scraping_service.py:
#   Este archivo recibe la petición HTTP y delega el trabajo real al servicio.
#   scraping_service.py es el que realmente va a los sitios y extrae los datos.
#   Es como un botón: este archivo es el botón, scraping_service.py es el motor.
#
# ENDPOINTS:
#   POST /scraping/run-scraping  → Inicia extracción de Carymar, Saraisa, OhMama
#   GET  /scraping/status        → Estado del último scraping ejecutado
#
# CÓMO PROBAR:
#   1. Ir a http://localhost:8000/docs
#   2. Expandir sección "Scraping"
#   3. Ejecutar POST /scraping/run-scraping
#   4. Luego verificar resultados en GET /products/
# ==============================================================================

from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from services.scraping_service import run_all_scrapers
from models.product import Product

router = APIRouter()


@router.post("/run-scraping", summary="Ejecutar scraping de todos los competidores")
def trigger_scraping(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Dispara la extracción de datos de Carymar, Saraisa y OhMama.

    La ejecución corre en SEGUNDO PLANO (background task) para que el
    servidor no se bloquee mientras trabaja. El endpoint responde
    inmediatamente con estado 'iniciado' y el scraping continúa.

    Una vez finalice, los resultados estarán disponibles en GET /products/
    """
    background_tasks.add_task(run_all_scrapers, db)

    return {
        "status":   "iniciado",
        "mensaje":  "Scraping lanzado en segundo plano para Carymar, Saraisa y OhMama.",
        "siguiente": "Espera unos minutos y consulta GET /products/ para ver los resultados."
    }


@router.get("/status", summary="Estado del último scraping")
def scraping_status(db: Session = Depends(get_db)):
    """
    Muestra cuándo fue la última vez que el sistema extrajo datos
    y cuántos productos hay registrados en total.
    """
    ultimo_scraping  = db.query(func.max(Product.scraped_at)).scalar()
    total_productos  = db.query(func.count(Product.id)).scalar() or 0

    por_competidor = (
        db.query(Product.competitor, func.count(Product.id).label("total"))
        .group_by(Product.competitor)
        .all()
    )

    return {
        "ultimo_scraping":          ultimo_scraping,
        "total_productos_en_bd":    total_productos,
        "productos_por_competidor": {row.competitor: row.total for row in por_competidor}
    }
