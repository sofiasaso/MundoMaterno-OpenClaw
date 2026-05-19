# ==============================================================================
# ARCHIVO 7: /backend/routes/metrics.py
# TIPO: Router / Controlador API (Python)
# FUNCIÓN: Calcula y expone métricas ejecutivas en tiempo real sobre los
#          datos de precios y productos de Carymar, Saraisa y OhMama.
#          Alimenta las gráficas Chart.js del dashboard de Mundo Materno.
#
# ENDPOINT:
#   GET /metrics/   → Resumen ejecutivo con totales, promedios y rankings
#
# CÓMO PROBAR:
#   Primero ejecutar un scraping (POST /scraping/run-scraping)
#   Luego consultar GET /metrics/ para ver los datos calculados
# ==============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from database.connection import get_db
from models.product import Product
from models.price_history import PriceHistory

router = APIRouter()


@router.get("/", summary="Métricas ejecutivas del mercado competidor")
def get_metrics(db: Session = Depends(get_db)):
    """
    Devuelve un resumen ejecutivo con:
    - Total de productos monitoreados
    - Promedio de precios global y por competidor
    - Competidor con precio promedio más bajo
    - Total de cambios de precio detectados
    - Desglose por categoría
    """

    # ─── Totales generales ────────────────────────────────────
    total_productos = db.query(func.count(Product.id)).scalar() or 0
    total_cambios   = db.query(func.count(PriceHistory.id)).scalar() or 0

    # ─── Promedio global de precios ───────────────────────────
    avg_global = db.query(func.avg(Product.price)).scalar()
    avg_global = round(avg_global, 2) if avg_global else 0.0

    # ─── Resumen por competidor ───────────────────────────────
    por_competidor = (
        db.query(
            Product.competitor,
            func.count(Product.id).label("total"),
            func.avg(Product.price).label("promedio"),
            func.min(Product.price).label("minimo"),
            func.max(Product.price).label("maximo"),
        )
        .group_by(Product.competitor)
        .all()
    )

    competidores = [
        {
            "competitor":         row.competitor,
            "total_productos":    row.total,
            "precio_promedio":    round(row.promedio, 2),
            "precio_minimo":      round(row.minimo, 2),
            "precio_maximo":      round(row.maximo, 2),
        }
        for row in por_competidor
    ]

    # ─── Competidor más barato ────────────────────────────────
    mas_barato = (
        min(competidores, key=lambda x: x["precio_promedio"])
        if competidores else None
    )

    # ─── Resumen por categoría ────────────────────────────────
    por_categoria = (
        db.query(
            Product.category,
            func.count(Product.id).label("total"),
            func.avg(Product.price).label("promedio"),
        )
        .group_by(Product.category)
        .order_by(func.avg(Product.price).desc())
        .all()
    )

    categorias = [
        {
            "category":        row.category,
            "total_productos": row.total,
            "precio_promedio": round(row.promedio, 2),
        }
        for row in por_categoria
    ]

    return {
        "resumen_general": {
            "total_productos":          total_productos,
            "total_cambios_detectados": total_cambios,
            "precio_promedio_global":   avg_global,
        },
        "competidor_mas_barato": mas_barato,
        "por_competidor":        competidores,
        "por_categoria":         categorias,
    }
