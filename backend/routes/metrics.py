# ==============================================================================
# ARCHIVO: /backend/routes/metrics.py
# FUNCIÓN:
# Genera métricas generales para el dashboard de Mundo Materno.
# ==============================================================================
print(">>> METRICS IMPORTADO REAL")

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from models.product import Product
from models.price_history import PriceHistory

router = APIRouter()


@router.get("/dashboard")
def dashboard_metrics(db: Session = Depends(get_db)):

    total_productos = db.query(func.count(Product.id)).scalar() or 0

    total_cambios = db.query(func.count(PriceHistory.id)).scalar() or 0

    promedio_global = (
        db.query(func.avg(Product.price)).scalar() or 0
    )

    # ==============================
    # MÉTRICAS POR COMPETIDOR
    # ==============================

    competidores = (
        db.query(
            Product.competitor,
            func.count(Product.id).label("total_productos"),
            func.avg(Product.price).label("precio_promedio"),
            func.min(Product.price).label("precio_minimo"),
            func.max(Product.price).label("precio_maximo")
        )
        .group_by(Product.competitor)
        .all()
    )

    por_competidor = []

    for c in competidores:
        por_competidor.append({
            "competitor": c.competitor,
            "total_productos": c.total_productos,
            "precio_promedio": round(c.precio_promedio, 2),
            "precio_minimo": c.precio_minimo,
            "precio_maximo": c.precio_maximo
        })

    # ==============================
    # COMPETIDOR MÁS BARATO
    # ==============================

    competidor_barato = None

    if por_competidor:
        competidor_barato = min(
            por_competidor,
            key=lambda x: x["precio_promedio"]
        )

    # ==============================
    # MÉTRICAS POR CATEGORÍA
    # ==============================

    categorias = (
        db.query(
            Product.category,
            func.count(Product.id).label("total_productos"),
            func.avg(Product.price).label("precio_promedio")
        )
        .group_by(Product.category)
        .order_by(func.avg(Product.price).desc())
        .all()
    )

    por_categoria = []

    for cat in categorias:
        por_categoria.append({
            "category": cat.category,
            "total_productos": cat.total_productos,
            "precio_promedio": round(cat.precio_promedio, 2)
        })

    return {
        "resumen_general": {
            "total_productos": total_productos,
            "total_cambios_detectados": total_cambios,
            "precio_promedio_global": round(promedio_global, 2)
        },

        "competidor_mas_barato": competidor_barato,

        "por_competidor": por_competidor,

        "por_categoria": por_categoria
    }
