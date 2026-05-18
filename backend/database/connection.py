# ==============================================================================
# ARCHIVO 2: /backend/database/connection.py
# TIPO: Script de configuración de base de datos (Python)
# FUNCIÓN: Establece la conexión con SQLite mediante SQLAlchemy.
#          Exporta el engine, la sesión y la Base declarativa que
#          todos los modelos del sistema usan para crear sus tablas.
#
# NOTA TÉCNICA:
#   SQLite no requiere instalar ningún servidor externo. El archivo
#   .db se crea automáticamente en la ruta indicada al levantar
#   el backend por primera vez.
#
# ARCHIVO GENERADO: /data/mundomaterno.db
# ==============================================================================

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Ruta al archivo de base de datos SQLite.
# Si existe la variable de entorno DATABASE_URL en .env, la usa.
# Si no, crea el archivo en la carpeta data/ del proyecto.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/mundomaterno.db")

# ─── Engine ───────────────────────────────────────────────────
# check_same_thread=False es obligatorio en SQLite cuando se usa
# con FastAPI, porque FastAPI maneja peticiones en múltiples hilos.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ─── SessionLocal ─────────────────────────────────────────────
# Fábrica de sesiones. Cada petición HTTP abre su propia sesión
# y la cierra al terminar. Así se evitan conflictos entre peticiones.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ─── Base declarativa ─────────────────────────────────────────
# Clase base de la que heredan todos los modelos ORM.
# SQLAlchemy la usa para registrar las tablas antes de crearlas.
Base = declarative_base()


# ─── Dependencia de sesión para FastAPI ───────────────────────
# Esta función se inyecta en los routers con Depends(get_db).
# Garantiza que la sesión se cierre siempre, incluso si hay error.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
