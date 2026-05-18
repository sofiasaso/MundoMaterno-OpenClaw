# ==============================================================================
# ARCHIVO 3: /backend/database/init_db.py
# TIPO: Script de inicialización (Python)
# FUNCIÓN: Crea automáticamente todas las tablas en SQLite al arrancar
#          el servidor. Importa los modelos para que SQLAlchemy los
#          registre en la Base antes de ejecutar CREATE TABLE.
#
# IMPORTANTE:
#   Este archivo NO borra datos existentes. Si las tablas ya existen,
#   las deja intactas. Es seguro ejecutarlo múltiples veces.
#
# SE LLAMA DESDE: main.py en el evento @app.on_event("startup")
# ==============================================================================

from database.connection import engine, Base

# Los modelos DEBEN importarse aquí aunque no se usen directamente.
# Sin estos imports, SQLAlchemy no los registra en la Base y no
# crea sus tablas al ejecutar create_all().
from models.product import Product           # noqa: F401 — import requerido
from models.price_history import PriceHistory  # noqa: F401 — import requerido


def init_db():
    """
    Crea todas las tablas definidas en los modelos ORM.
    Usa CREATE TABLE IF NOT EXISTS internamente, así que es idempotente.

    Tablas que crea:
      - products       → productos extraídos de Carymar, Saraisa, OhMama
      - price_history  → historial de cambios de precio por producto
    """
    print("Verificando tablas en SQLite...")
    Base.metadata.create_all(bind=engine)
    print("Tablas verificadas: products, price_history")


# Permite ejecutar este archivo directamente para inicializar la DB
# sin necesidad de levantar el servidor completo:
#   python database/init_db.py
if __name__ == "__main__":
    init_db()
    print("Base de datos inicializada correctamente.")
