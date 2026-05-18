# app/services/scraping_service.py

import requests
import pandas as pd
import numpy as np
import re
import unicodedata
import time

from bs4 import BeautifulSoup
from pathlib import Path
from collections import Counter

from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.model_selection import (
    train_test_split,
    StratifiedKFold,
    KFold,
    cross_val_score
)
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.compose import ColumnTransformer, TransformedTargetRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    classification_report,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    make_scorer
)

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

# =========================================================
# SCRAPING CARYMAR
# =========================================================

def scrape_carymar():

    base_url = "https://www.carymar.co"
    productos = []

    response = requests.get(base_url, headers=HEADERS)
    soup = BeautifulSoup(response.text, "html.parser")

    colecciones = []

    for link in soup.select("a[href*='/collections/']"):
        url = link.get("href")

        if url and "/collections/" in url and "all" not in url:

            url = base_url + url if url.startswith("/") else url

            if url not in colecciones:
                colecciones.append(url)

    print(f"[CARYMAR] Colecciones encontradas: {len(colecciones)}")

    for coleccion_url in colecciones:

        page = 1

        while True:

            url = coleccion_url if page == 1 else f"{coleccion_url}?page={page}"

            response = requests.get(url, headers=HEADERS)
            soup = BeautifulSoup(response.text, "html.parser")

            items = soup.select("div.product-card")

            if not items:
                break

            for item in items:

                nombre_tag = item.select_one("div.grid-view-item__title")
                nombre = nombre_tag.get_text(strip=True) if nombre_tag else "N/A"

                precio_tag = (
                    item.select_one("span.price-item--sale")
                    or item.select_one("span.price-item--regular")
                )

                precio = precio_tag.get_text(strip=True) if precio_tag else "N/A"

                enlace_tag = item.select_one("a")

                enlace = (
                    base_url + enlace_tag["href"]
                    if enlace_tag else None
                )

                colores = []
                descripcion = "N/A"

                if enlace:

                    try:

                        resp_prod = requests.get(enlace, headers=HEADERS)
                        soup_prod = BeautifulSoup(resp_prod.text, "html.parser")

                        color_tags = (
                            soup_prod.select("input[name='Color'][type='radio'] + label")
                            or soup_prod.select("option")
                        )

                        colores = [
                            c.get_text(strip=True)
                            for c in color_tags
                            if c.get_text(strip=True)
                        ]

                        desc_tag = soup_prod.select_one(
                            "div.product-single__description"
                        )

                        if desc_tag:
                            descripcion = desc_tag.get_text(strip=True)

                    except Exception as e:
                        print(f"[CARYMAR] Error producto: {e}")

                productos.append({
                    "Categoria": coleccion_url.split("/")[-1],
                    "Producto": nombre,
                    "Precio": precio,
                    "Colores": ", ".join(colores) if colores else "N/A",
                    "Descripcion": descripcion,
                    "URL": enlace,
                    "Tienda": "Carymar"
                })

                time.sleep(1)

            page += 1

    return pd.DataFrame(productos)

# =========================================================
# SCRAPING SARAISA
# =========================================================

def scrape_saraisa():

    base_url = "https://saraisa.co"

    categorias = []
    productos = []

    resp = requests.get(f"{base_url}/tienda/", headers=HEADERS)
    soup = BeautifulSoup(resp.text, "html.parser")

    links = soup.select('a[href*="/categoria-producto/"]')

    for link in links:

        url = link["href"]

        if url not in categorias:
            categorias.append(url)

    print(f"[SARAISA] Categorías encontradas: {len(categorias)}")

    for cat_url in categorias:

        resp = requests.get(cat_url, headers=HEADERS)
        soup = BeautifulSoup(resp.text, "html.parser")

        items = soup.select("div.nm-shop-loop-title-price")

        for item in items:

            nombre_tag = item.select_one(
                "h3.woocommerce-loop-product__title a"
            )

            nombre = (
                nombre_tag.get_text(strip=True)
                if nombre_tag else "N/A"
            )

            url_producto = (
                nombre_tag["href"]
                if nombre_tag else "N/A"
            )

            precio_tag = (
                item.select_one(
                    "span.price ins .woocommerce-Price-amount"
                )
                or item.select_one(
                    "span.price .woocommerce-Price-amount"
                )
            )

            precio = (
                precio_tag.get_text(strip=True)
                if precio_tag else "N/A"
            )

            descripcion = ""
            colores = ""
            estampados = ""
            tallas = ""

            if url_producto != "N/A":

                resp_p = requests.get(url_producto, headers=HEADERS)
                soup_p = BeautifulSoup(resp_p.text, "html.parser")

                desc_tag = soup_p.select_one(
                    "div.woocommerce-product-details__short-description"
                )

                if desc_tag:
                    descripcion = desc_tag.get_text(strip=True)

                colores = ", ".join([
                    o.get("value")
                    for o in soup_p.select("#pa_colores option")
                    if o.get("value")
                ])

                estampados = ", ".join([
                    o.get("value")
                    for o in soup_p.select("#pa_estampado option")
                    if o.get("value")
                ])

                tallas = ", ".join([
                    o.get("value")
                    for o in soup_p.select("#pa_tallas option")
                    if o.get("value")
                ])

                time.sleep(1)

            productos.append({
                "Categoria": cat_url.split("/")[-2],
                "Producto": nombre,
                "Precio": precio,
                "Descripcion": descripcion,
                "Colores": colores,
                "Estampados": estampados,
                "Tallas": tallas,
                "URL": url_producto,
                "Tienda": "Saraisa"
            })

    return pd.DataFrame(productos)

# =========================================================
# UTILIDADES LIMPIEZA
# =========================================================

def parse_precio(x):

    if pd.isna(x):
        return np.nan

    s = str(x)

    s = s.replace("$", "").replace(",", "").strip()

    if s.endswith(".00"):
        s = s[:-3]

    s = re.sub(r"[^\d]", "", s)

    return float(s) if s else np.nan


def norm_text(s):

    if pd.isna(s):
        return s

    s = str(s).lower()

    s = unicodedata.normalize("NFKD", s)

    s = "".join(
        ch for ch in s
        if not unicodedata.category(ch).startswith("M")
    )

    s = s.replace("+", " ")
    s = s.replace("_", " ")
    s = s.replace("-", " ")

    s = re.sub(r"\s+", " ", s).strip()

    return s

# =========================================================
# CONSOLIDACIÓN
# =========================================================

def consolidar_datasets(*dfs):

    df_final = pd.concat(dfs, ignore_index=True)

    df_final["Precio_num"] = df_final["Precio"].apply(parse_precio)

    return df_final

# =========================================================
# NLP / FEATURES
# =========================================================

def construir_texto(df):

    df["texto"] = (
        df["Producto"].fillna("")
        + " "
        + df["Descripcion"].fillna("")
    )

    return df

# =========================================================
# MODELO NLP CATEGORÍAS
# =========================================================

def entrenar_modelo_categoria(df):

    X = df["texto"]
    y = df["Categoria_norm"]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        stratify=y,
        test_size=0.1,
        random_state=42
    )

    pipe = Pipeline([
        (
            "tfidf",
            TfidfVectorizer(
                max_features=8000,
                ngram_range=(1, 2)
            )
        ),
        (
            "clf",
            LogisticRegression(
                max_iter=4000,
                class_weight="balanced",
                n_jobs=-1
            )
        )
    ])

    pipe.fit(X_train, y_train)

    pred = pipe.predict(X_test)

    print(classification_report(y_test, pred))

    return pipe

# =========================================================
# MODELO REGRESIÓN PRECIO
# =========================================================

def entrenar_modelo_precio(df):

    X = df[["texto", "Categoria_norm"]]
    y = df["Precio_num"]

    pre = ColumnTransformer([
        (
            "tfidf",
            TfidfVectorizer(
                max_features=8000,
                ngram_range=(1, 2)
            ),
            "texto"
        ),
        (
            "cat",
            OneHotEncoder(handle_unknown="ignore"),
            ["Categoria_norm"]
        )
    ])

    model = TransformedTargetRegressor(

        regressor=Pipeline([
            ("pre", pre),
            (
                "rf",
                RandomForestRegressor(
                    n_estimators=400,
                    random_state=42,
                    n_jobs=-1
                )
            )
        ]),

        func=np.log1p,
        inverse_func=np.expm1
    )

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    model.fit(X_train, y_train)

    pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, pred)
    rmse = np.sqrt(mean_squared_error(y_test, pred))
    r2 = r2_score(y_test, pred)

    print(f"MAE: {mae:,.0f}")
    print(f"RMSE: {rmse:,.0f}")
    print(f"R2: {r2:.3f}")

    return model

# =========================================================
# EXPORTACIÓN
# =========================================================

def exportar_csv(df, nombre):

    Path("salidas").mkdir(exist_ok=True)

    ruta = f"salidas/{nombre}.csv"

    df.to_csv(ruta, index=False, encoding="utf-8-sig")

    print(f"CSV guardado: {ruta}")
