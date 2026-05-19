# ==============================================================================
# ARCHIVO 10: /backend/services/scraping_service.py
# TIPO: Servicio de lógica de negocio / Coordinador de scrapers (Python)
# FUNCIÓN: Cerebro del sistema de inteligencia competitiva de Mundo Materno.
#          Contiene los scrapers REALES para Carymar, Saraisa y OhMama,
#          basados en el notebook del equipo (Ropamaterna_web_scrapping).
#          Coordina la extracción, normaliza precios, detecta duplicados,
#          registra cambios de precio y guarda todo en SQLite.
#
# DIFERENCIA CON routes/scraping.py:
#   routes/scraping.py es el botón (recibe el click del usuario).
#   Este archivo es el motor (hace todo el trabajo real).
#
# SCRAPERS INCLUIDOS:
#   1. scrape_carymar  → www.carymar.co   (Shopify, colecciones paginadas)
#   2. scrape_saraisa  → saraisa.co       (WooCommerce, categorías)
#   3. scrape_ohmama   → www.ohmama.com.co (Shopify, colecciones)
#
# CÓMO FUNCIONA EL FLUJO:
#   run_all_scrapers()
#     → llama a cada scraper individual
#     → recibe lista de productos como dicts
#     → llama a _normalizar_precio() para limpiar "$55.000" → 55000.0
#     → llama a _guardar_producto() para cada producto
#       → si ya existe: detecta cambio de precio y registra en price_history
#       → si es nuevo: lo inserta en products
#     → hace commit final a SQLite
# ==============================================================================

import time
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from sqlalchemy.orm import Session

from models.product import Product
from models.price_history import PriceHistory

# ─── Configuración global ─────────────────────────────────────
HEADERS = {"User-Agent": "Mozilla/5.0"}
DELAY   = 1  # segundos entre peticiones para no sobrecargar los sitios


# ==============================================================================
# UTILIDADES
# ==============================================================================

def _normalizar_precio(precio_str: str) -> float | None:
    """
    Convierte strings de precio colombiano a float.

    Ejemplos:
      "$55.000"   → 55000.0
      "$106,250"  → 106250.0
      "$1.200.000"→ 1200000.0
      "N/A"       → None

    El notebook del equipo extrae los precios como strings con símbolo $,
    puntos de miles y comas decimales. Esta función los normaliza todos.
    """
    if not precio_str or precio_str == "N/A":
        return None
    try:
        limpio = precio_str.replace("$", "").replace("\xa0", "").strip()
        # Formato colombiano con punto como separador de miles: $55.000
        if "." in limpio and "," not in limpio:
            limpio = limpio.replace(".", "")
        # Formato con coma como separador de miles: $106,250
        elif "," in limpio and "." not in limpio:
            limpio = limpio.replace(",", "")
        # Formato mixto: $1.200,50
        elif "." in limpio and "," in limpio:
            limpio = limpio.replace(".", "").replace(",", ".")
        return float(limpio)
    except (ValueError, AttributeError):
        return None


# ==============================================================================
# SCRAPER 1: CARYMAR (www.carymar.co)
# Basado directamente en el notebook del equipo.
# Shopify: navega colecciones paginadas y entra a cada producto.
# ==============================================================================

def scrape_carymar() -> list[dict]:
    """
    Extrae productos de www.carymar.co.
    Lógica replicada del notebook: descubre colecciones desde la home,
    las recorre página por página y extrae nombre, precio, colores y URL.

    Retorna lista de dicts con claves:
      name, price, category, competitor, product_url
    """
    base_url = "https://www.carymar.co"
    productos = []

    try:
        # Paso 1: descubrir colecciones desde la home
        resp = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        colecciones = []
        for link in soup.select("a[href*='/collections/']"):
            url = link.get("href")
            if url and "/collections/" in url and "all" not in url:
                url_completa = base_url + url if url.startswith("/") else url
                if url_completa not in colecciones:
                    colecciones.append(url_completa)

        print(f"[Carymar] {len(colecciones)} colecciones encontradas.")

        # Paso 2: recorrer cada colección página por página
        for coleccion_url in colecciones:
            page = 1
            while True:
                url = coleccion_url if page == 1 else f"{coleccion_url}?page={page}"

                try:
                    resp = requests.get(url, headers=HEADERS, timeout=15)
                    soup = BeautifulSoup(resp.text, "html.parser")

                    items = soup.select("div.product-card")
                    if not items:
                        break  # No hay más páginas

                    for item in items:
                        nombre_tag = item.select_one("div.grid-view-item__title")
                        nombre     = nombre_tag.get_text(strip=True) if nombre_tag else None
                        if not nombre:
                            continue

                        precio_tag = (
                            item.select_one("span.price-item--sale")
                            or item.select_one("span.price-item--regular")
                        )
                        precio_raw = precio_tag.get_text(strip=True) if precio_tag else None
                        precio     = _normalizar_precio(precio_raw)
                        if precio is None:
                            continue

                        enlace_tag = item.select_one("a")
                        enlace     = base_url + enlace_tag["href"] if enlace_tag else None

                        categoria  = coleccion_url.rstrip("/").split("/")[-1]

                        productos.append({
                            "name":        nombre,
                            "price":       precio,
                            "category":    categoria,
                            "competitor":  "carymar",
                            "product_url": enlace,
                        })

                        time.sleep(DELAY)

                    page += 1

                except Exception as e:
                    print(f"[Carymar] Error en {url}: {e}")
                    break

    except Exception as e:
        print(f"[Carymar] Error general: {e}")

    print(f"[Carymar] {len(productos)} productos extraídos.")
    return productos


# ==============================================================================
# SCRAPER 2: SARAISA (saraisa.co)
# Basado directamente en el notebook del equipo.
# WooCommerce: navega categorías y extrae con selectores específicos.
# ==============================================================================

def scrape_saraisa() -> list[dict]:
    """
    Extrae productos de saraisa.co.
    Lógica replicada del notebook: descubre categorías desde /tienda/,
    luego recorre cada una extrayendo nombre, precio, colores, tallas.

    Retorna lista de dicts con claves:
      name, price, category, competitor, product_url
    """
    base_url = "https://saraisa.co"
    productos = []

    try:
        # Paso 1: descubrir categorías desde /tienda/
        resp = requests.get(f"{base_url}/tienda/", headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        categorias = []
        for link in soup.select('a[href*="/categoria-producto/"]'):
            url = link["href"]
            if url not in categorias:
                categorias.append(url)

        print(f"[Saraisa] {len(categorias)} categorías encontradas.")

        # Paso 2: recorrer cada categoría
        for cat_url in categorias:
            try:
                resp = requests.get(cat_url, headers=HEADERS, timeout=15)
                soup = BeautifulSoup(resp.text, "html.parser")

                items = soup.select("div.nm-shop-loop-title-price")

                for item in items:
                    nombre_tag = item.select_one("h3.woocommerce-loop-product__title a")
                    nombre     = nombre_tag.get_text(strip=True) if nombre_tag else None
                    if not nombre:
                        continue

                    url_producto = nombre_tag["href"] if nombre_tag else None

                    precio_tag = (
                        item.select_one("span.price ins .woocommerce-Price-amount")
                        or item.select_one("span.price .woocommerce-Price-amount")
                    )
                    precio_raw = precio_tag.get_text(strip=True) if precio_tag else None
                    precio     = _normalizar_precio(precio_raw)
                    if precio is None:
                        continue

                    categoria = cat_url.rstrip("/").split("/")[-1]

                    productos.append({
                        "name":        nombre,
                        "price":       precio,
                        "category":    categoria,
                        "competitor":  "saraisa",
                        "product_url": url_producto,
                    })

                    time.sleep(DELAY)

            except Exception as e:
                print(f"[Saraisa] Error en {cat_url}: {e}")

    except Exception as e:
        print(f"[Saraisa] Error general: {e}")

    print(f"[Saraisa] {len(productos)} productos extraídos.")
    return productos


# ==============================================================================
# SCRAPER 3: OHMAMA (www.ohmama.com.co)
# Basado en el notebook del equipo.
# Shopify: navega colecciones desde el menú principal.
# ==============================================================================

def scrape_ohmama() -> list[dict]:
    """
    Extrae productos de www.ohmama.com.co.
    Shopify: descubre colecciones desde el menú de navegación,
    luego las recorre página por página.

    Retorna lista de dicts con claves:
      name, price, category, competitor, product_url
    """
    base_url = "https://www.ohmama.com.co"
    productos = []

    try:
        # Paso 1: descubrir colecciones desde el menú
        resp = requests.get(base_url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(resp.text, "html.parser")

        categorias = []
        for link in soup.select("ul.list-menu li a"):
            url = link.get("href")
            if url and "/collections/" in url:
                url_completa = base_url + url if url.startswith("/") else url
                if url_completa not in categorias:
                    categorias.append(url_completa)

        print(f"[OhMama] {len(categorias)} colecciones encontradas.")

        # Paso 2: recorrer cada colección
        for cat_url in categorias:
            page = 1
            while True:
                url = cat_url if page == 1 else f"{cat_url}?page={page}"

                try:
                    resp = requests.get(url, headers=HEADERS, timeout=15)
                    soup = BeautifulSoup(resp.text, "html.parser")

                    # OhMama también usa Shopify, selectores similares a Carymar
                    items = soup.select("div.product-card, li.grid__item")
                    if not items:
                        break

                    for item in items:
                        nombre_tag = (
                            item.select_one("div.card__heading a")
                            or item.select_one("h3.grid-view-item__title")
                            or item.select_one(".card__heading")
                        )
                        nombre = nombre_tag.get_text(strip=True) if nombre_tag else None
                        if not nombre:
                            continue

                        precio_tag = (
                            item.select_one("span.price-item--sale")
                            or item.select_one("span.price-item--regular")
                            or item.select_one(".price__regular .price-item")
                        )
                        precio_raw = precio_tag.get_text(strip=True) if precio_tag else None
                        precio     = _normalizar_precio(precio_raw)
                        if precio is None:
                            continue

                        enlace_tag = nombre_tag.get("href") if nombre_tag else None
                        enlace     = base_url + enlace_tag if enlace_tag and enlace_tag.startswith("/") else enlace_tag

                        categoria  = cat_url.rstrip("/").split("/")[-1]

                        productos.append({
                            "name":        nombre,
                            "price":       precio,
                            "category":    categoria,
                            "competitor":  "ohmama",
                            "product_url": enlace,
                        })

                        time.sleep(DELAY)

                    page += 1

                except Exception as e:
                    print(f"[OhMama] Error en {url}: {e}")
                    break

    except Exception as e:
        print(f"[OhMama] Error general: {e}")

    print(f"[OhMama] {len(productos)} productos extraídos.")
    return productos


# ==============================================================================
# ORQUESTADOR PRINCIPAL
# Coordinado por OpenClaw. Llama a los tres scrapers, consolida resultados
# y persiste todo en SQLite con detección de duplicados y cambios de precio.
# ==============================================================================

def run_all_scrapers(db: Session) -> dict:
    """
    Ejecuta los tres scrapers en secuencia y guarda los resultados en SQLite.

    Flujo por cada producto:
      1. Verifica si ya existe en la base de datos (mismo nombre + competidor).
      2. Si existe y el precio cambió: registra el cambio en price_history.
      3. Si es nuevo: lo inserta como nuevo registro en products.
      4. Si existe y el precio es igual: lo ignora (sin duplicados).

    Retorna un resumen de ejecución con totales y errores por competidor.
    """
    resumen = {
        "inicio":       datetime.utcnow().isoformat(),
        "competidores": [],
        "total_procesados": 0,
        "total_nuevos":     0,
        "total_actualizados": 0,
        "errores":      []
    }

    scrapers = [
        ("carymar", scrape_carymar),
        ("saraisa", scrape_saraisa),
        ("ohmama",  scrape_ohmama),
    ]

    for nombre_competidor, funcion_scraper in scrapers:
        print(f"\n{'='*50}")
        print(f"Iniciando scraping: {nombre_competidor.upper()}")
        print(f"{'='*50}")

        try:
            productos_raw  = funcion_scraper()
            nuevos, actualizados = _persistir_productos(db, productos_raw)

            resumen["competidores"].append({
                "competidor":   nombre_competidor,
                "extraidos":    len(productos_raw),
                "nuevos":       nuevos,
                "actualizados": actualizados,
                "estado":       "ok"
            })
            resumen["total_procesados"]  += len(productos_raw)
            resumen["total_nuevos"]      += nuevos
            resumen["total_actualizados"] += actualizados

            print(f"[{nombre_competidor.upper()}] OK: {nuevos} nuevos, {actualizados} actualizados.")

        except Exception as e:
            msg = f"Error en {nombre_competidor}: {str(e)}"
            resumen["errores"].append(msg)
            resumen["competidores"].append({
                "competidor": nombre_competidor,
                "estado":     "error",
                "detalle":    str(e)
            })
            print(f"[{nombre_competidor.upper()}] ERROR: {e}")

    resumen["fin"] = datetime.utcnow().isoformat()
    print(f"\nScraping finalizado. Total procesados: {resumen['total_procesados']}")
    return resumen


def _persistir_productos(db: Session, productos: list[dict]) -> tuple[int, int]:
    """
    Guarda la lista de productos en SQLite.

    - Detecta duplicados por nombre + competidor.
    - Si el precio cambió, registra el cambio en price_history.
    - Si es nuevo, lo inserta.

    Retorna (nuevos, actualizados) como contadores.
    """
    nuevos      = 0
    actualizados = 0

    for item in productos:
        nombre      = item.get("name", "").strip()
        competidor  = item.get("competitor", "").strip()
        precio      = item.get("price")

        if not nombre or not competidor or precio is None:
            continue

        existente = (
            db.query(Product)
            .filter(
                Product.name       == nombre,
                Product.competitor == competidor
            )
            .first()
        )

        if existente:
            # Comparar precios con tolerancia de 1 peso para evitar
            # falsos positivos por redondeo de float
            if abs(existente.price - precio) > 1:
                historial = PriceHistory(
                    product_id  = existente.id,
                    old_price   = existente.price,
                    new_price   = precio,
                    detected_at = datetime.utcnow()
                )
                db.add(historial)
                existente.price      = precio
                existente.scraped_at = datetime.utcnow()
                actualizados += 1
        else:
            nuevo = Product(
                name        = nombre,
                category    = item.get("category", "sin categoria"),
                price       = precio,
                competitor  = competidor,
                product_url = item.get("product_url"),
                scraped_at  = datetime.utcnow()
            )
            db.add(nuevo)
            nuevos += 1

    db.commit()
    return nuevos, actualizados
