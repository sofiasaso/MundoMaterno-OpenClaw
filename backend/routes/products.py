# ==============================================================================
# ARCHIVO 6: /backend/routes/products.py
# TIPO: Router / Controlador API (Python)
# FUNCIÓN: Expone los endpoints HTTP para consultar productos extraídos
#          de Carymar, Saraisa y OhMama almacenados en SQLite.
#
# ENDPOINTS:
#   GET /products/       → Lista todos los productos (con filtros opcionales)
#   GET /products/{id}   → Detalle de un producto con historial de precios
#
# CÓMO PROBAR:
#   Ir a http://localhost:8000/docs y expandir la sección "Productos"
#   o usar: GET /products/?competitor=carymar
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from database.connection import get_db
from models.product import Product

router = APIRouter()


@router.get("/", summary="Listar productos de la competencia")
def get_products(
    competitor: Optional[str] = Query(None, description="carymar | saraisa | ohmama"),
    category:   Optional[str] = Query(None, description="vestidos, blusas, jeans..."),
    limit:      int            = Query(200, le=1000),
    db:         Session        = Depends(get_db)
):
    """
    Devuelve todos los productos registrados.
    Filtra por competidor y/o categoría de forma opcional.
    """
    try:
        query = db.query(Product)
        if competitor:
            query = query.filter(Product.competitor == competitor.lower())
        if category:
            query = query.filter(Product.category.ilike(f"%{category}%"))

        productos = query.order_by(Product.scraped_at.desc()).limit(limit).all()

        return {
            "total": len(productos),
            "filtros": {"competitor": competitor, "category": category},
            "products": [
                {
                    "id":          p.id,
                    "name":        p.name,
                    "category":    p.category,
                    "price":       p.price,
                    "competitor":  p.competitor,
                    "product_url": p.product_url,
                    "scraped_at":  p.scraped_at,
                }
                for p in productos
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{product_id}", summary="Detalle de un producto con historial de precios")
def get_product(product_id: int, db: Session = Depends(get_db)):
    """
    Detalle completo de un producto y su historial de cambios de precio.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail=f"Producto {product_id} no encontrado.")

    return {
        "id":            product.id,
        "name":          product.name,
        "category":      product.category,
        "price":         product.price,
        "competitor":    product.competitor,
        "product_url":   product.product_url,
        "scraped_at":    product.scraped_at,
        "price_history": [
            {
                "old_price":     h.old_price,
                "new_price":     h.new_price,
                "reduction_pct": h.reduction_pct,
                "detected_at":   h.detected_at,
            }
            for h in product.price_history
        ]
    }
