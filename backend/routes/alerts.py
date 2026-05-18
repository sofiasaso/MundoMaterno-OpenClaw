# ==============================================================================
# ARCHIVO 8: /backend/routes/alerts.py
# TIPO: Router / Controlador API (Python)
# FUNCIÓN: Analiza el historial de precios y genera alertas ejecutivas
#          cuando detecta reducciones de precio significativas en los
#          productos de Carymar, Saraisa u OhMama.
#
# ENDPOINT:
#   GET /alerts/   → Lista de alertas ordenadas por mayor reducción
#
# LÓGICA:
#   Se genera una alerta cuando new_price < old_price en al menos 10%.
#   El umbral del 10% viene del objetivo específico del proyecto.
# ==============================================================================

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.connection import get_db
from models.price_history import PriceHistory
from models.product import Product

router = APIRouter()

UMBRAL_ALERTA = 0.10  # 10% de reducción mínima para generar alerta


@router.get("/", summary="Alertas de reducciones de precio de la competencia")
def get_alerts(db: Session = Depends(get_db)):
    """
    Detecta y devuelve todas las reducciones de precio iguales o
    mayores al 10% registradas en el historial.
    Ordenadas de mayor a menor reducción porcentual.

    Útil para que Mundo Materno decida si debe ajustar sus precios
    en respuesta a movimientos de la competencia.
    """

    registros = (
        db.query(PriceHistory, Product)
        .join(Product, PriceHistory.product_id == Product.id)
        .all()
    )

    alertas = []

    for historial, producto in registros:
        if historial.old_price <= 0:
            continue

        reduccion = (historial.old_price - historial.new_price) / historial.old_price

        if reduccion >= UMBRAL_ALERTA:
            pct = round(reduccion * 100, 1)
            alertas.append({
                "product_id":    producto.id,
                "product_name":  producto.name,
                "category":      producto.category,
                "competitor":    producto.competitor,
                "old_price":     historial.old_price,
                "new_price":     historial.new_price,
                "reduction_pct": pct,
                "detected_at":   historial.detected_at,
                "product_url":   producto.product_url,
                "mensaje": (
                    f"{producto.competitor.upper()} redujo '{producto.name}' "
                    f"un {pct}%: de ${historial.old_price:,.0f} "
                    f"a ${historial.new_price:,.0f} COP."
                )
            })

    alertas.sort(key=lambda x: x["reduction_pct"], reverse=True)

    return {
        "total_alertas":  len(alertas),
        "umbral_pct":     UMBRAL_ALERTA * 100,
        "alertas":        alertas
    }
