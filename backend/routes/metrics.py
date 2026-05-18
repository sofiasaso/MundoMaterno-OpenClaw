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

    competidores = (
        db.query(
            Product.competitor,
            func.count(Product.id).label("total_productos"),
            func.avg(Product.price).label("precio_promedio"),
            func.min(Product.price).label("precio_minimo"),
            func.max(Product.price).label("precio_maximo"),
        )
        .group_by(Product.competitor)
        .all()
    )

    categorias = (
        db.query(
            Product.category,
            func.count(Product.id).label("total_productos"),
            func.avg(Product.price).label("precio_promedio"),
        )
        .group_by(Product.category)
        .all()
    )

    competidor_barato = min(
        competidores,
        key=lambda x: x.precio_promedio
    ) if competidores else None

    return {
        "resumen_general": {
            "total_productos": total_productos,
            "total_cambios_detectados": total_cambios,
            "precio_promedio_global": round(promedio_global, 2),
        },

        "competidor_mas_barato": {
            "competitor": competidor_barato.competitor,
            "total_productos": competidor_barato.total_productos,
            "precio_promedio": round(competidor_barato.precio_promedio, 2),
            "precio_minimo": competidor_barato.precio_minimo,
            "precio_maximo": competidor_barato.precio_maximo,
        } if competidor_barato else None,

        "por_competidor": [
            {
                "competitor": c.competitor,
                "total_productos": c.total_productos,
                "precio_promedio": round(c.precio_promedio, 2),
                "precio_minimo": c.precio_minimo,
                "precio_maximo": c.precio_maximo,
            }
            for c in competidores
        ],

        "por_categoria": [
            {
                "category": cat.category,
                "total_productos": cat.total_productos,
                "precio_promedio": round(cat.precio_promedio, 2),
            }
            for cat in categorias
        ]
    }
