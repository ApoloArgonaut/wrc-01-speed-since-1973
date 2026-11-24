"""Métricas derivadas del archivo WRC.

La superficie NO se clasifica aquí: la publica el propio archivo en la ficha de
cada rally ("Surface: Gravel / Asphalt / Snow"), así que se usa tal cual. Eso
evita una decisión editorial y hace el resultado reproducible por cualquiera.

Todas las funciones son puras: reciben un DataFrame y devuelven otro.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

SUPERFICIES_VALIDAS = ("tierra", "asfalto", "nieve")


def velocidad_media(df: pd.DataFrame) -> pd.DataFrame:
    """Velocidad media del ganador en km/h.

    Es el único indicador comparable entre épocas: no depende de cuántos tramos
    tenga el rally, de su longitud, ni de dónde se corriera. Es distancia
    cronometrada dividida entre tiempo cronometrado.
    """
    df = df.copy()
    df["vel_kmh"] = df["distancia_tramos_km"] / (df["tiempo_s"] / 3600.0)
    return df


def tasa_finish(df: pd.DataFrame) -> pd.DataFrame:
    """Porcentaje de inscritos que terminan. Mide fiabilidad, no velocidad."""
    df = df.copy()
    df["tasa_finish"] = np.where(
        df["inscritos"].gt(0) & df["finalizados"].notna(),
        100.0 * df["finalizados"] / df["inscritos"],
        np.nan,
    )
    return df


def limpiar(df: pd.DataFrame) -> pd.DataFrame:
    """Descarta filas imposibles en vez de corregirlas a mano.

    Criterios, todos justificables:
      - velocidad media fuera de 40–160 km/h: no es un rally, es un error de
        extracción (distancia de un año con el tiempo de otro).
      - distancia de tramos menor a 50 km: un rally del WRC nunca fue tan corto.
      - clasificación de superficie vacía o no reconocida.

    Devuelve el DataFrame filtrado con `attrs` que documentan cuántas filas se
    descartaron y por qué — el número va al README, no se esconde.
    """
    antes = len(df)
    df = velocidad_media(df)
    df = tasa_finish(df)

    motivos = {}
    m = ~df["distancia_tramos_km"].between(50, 1200)
    motivos["distancia_imposible"] = int(m.sum())
    df = df[~m]

    m = ~df["vel_kmh"].between(40, 160)
    motivos["velocidad_imposible"] = int(m.sum())
    df = df[~m]

    m = ~df["superficie"].isin(SUPERFICIES_VALIDAS)
    motivos["superficie_desconocida"] = int(m.sum())
    df = df[~m]

    df = df.copy()
    df.attrs["descartados"] = antes - len(df)
    df.attrs["motivos"] = motivos
    return df


def resumen_por_decada(df: pd.DataFrame) -> pd.DataFrame:
    """Velocidad media por década y superficie, con conteo."""
    d = df.copy()
    d["decada"] = (d["anio"] // 10) * 10
    tabla = (d.groupby(["decada", "superficie"])["vel_kmh"]
              .agg(["mean", "count", "std"])
              .rename(columns={"mean": "vel_media", "count": "n", "std": "sd"}))
    tabla["ee"] = tabla["sd"] / np.sqrt(tabla["n"])
    return tabla.reset_index()


def control_por_distancia(df: pd.DataFrame, banda: tuple[int, int] = (250, 400)) -> pd.DataFrame:
    """Velocidad por década restringida a rallys de longitud comparable.

    Los rallys pasaron de ~574 km de tramos en los 70 a ~298 km en los 2020, y la
    longitud correlaciona negativamente con la velocidad media (Pearson -0.37):
    un rally largo incluye enlaces, tramos rotos y promedio más bajo. Comparar la
    media cruda de 1973 con la de 2025 mezcla ese efecto con el del coche.

    Restringir a una banda de distancia fija el confusor: dentro de la banda, la
    única cosa que cambia entre décadas es el coche y el trazado.
    """
    d = df[df["distancia_tramos_km"].between(*banda)].copy()
    d["decada"] = (d["anio"] // 10) * 10
    return (d.groupby("decada")["vel_kmh"]
             .agg(["mean", "count", "std"])
             .rename(columns={"mean": "vel_media", "count": "n", "std": "sd"})
             .reset_index())


def resumen_por_superficie(df: pd.DataFrame,
                           antes: tuple[int, int] = (1973, 1979),
                           despues: tuple[int, int] = (2020, 2026)) -> pd.DataFrame:
    """Velocidad media por superficie en los dos extremos del archivo."""
    filas = []
    for sup in ("nieve", "asfalto", "tierra"):
        s = df[df["superficie"] == sup]
        a = s[s["anio"].between(*antes)]["vel_kmh"]
        b = s[s["anio"].between(*despues)]["vel_kmh"]
        filas.append({
            "superficie": sup,
            "antes_media": float(a.mean()) if len(a) else float("nan"),
            "antes_n": int(len(a)),
            "despues_media": float(b.mean()) if len(b) else float("nan"),
            "despues_n": int(len(b)),
            "delta": float(b.mean() - a.mean()) if len(a) and len(b) else float("nan"),
        })
    return pd.DataFrame(filas)


def contraste_1981(df: pd.DataFrame, ventana: tuple[int, int] = (1975, 1987)) -> dict:
    """Contraste antes/después de la tracción total, por superficie.

    La pregunta es si el 4WD cambió la velocidad y si la cambió MÁS en las
    superficies donde la tracción importa (tierra, nieve) que en asfalto, donde
    un 2WD ya transmitía bien. Eso es una diferencia en diferencias: el cambio
    en asfalto actúa como control de todo lo demás que mejoró a la vez
    (neumáticos, potencia, frenos).

    Devuelve medias, deltas y la estimación DiD con su error estándar.
    """
    desde, hasta = ventana
    v = df[df["anio"].between(desde, hasta) & df["superficie"].isin(["tierra", "asfalto"])]
    pre = v[v["anio"] <= 1980]
    post = v[v["anio"] >= 1982]

    salida: dict = {"ventana": ventana, "grupos": {}}
    for sup in ("asfalto", "tierra"):
        a = pre[pre["superficie"] == sup]["vel_kmh"]
        b = post[post["superficie"] == sup]["vel_kmh"]
        salida["grupos"][sup] = {
            "pre_media": float(a.mean()) if len(a) else float("nan"),
            "pre_n": int(len(a)),
            "post_media": float(b.mean()) if len(b) else float("nan"),
            "post_n": int(len(b)),
            "delta": float(b.mean() - a.mean()) if len(a) and len(b) else float("nan"),
            "pre_ee": float(a.std(ddof=1) / np.sqrt(len(a))) if len(a) > 1 else float("nan"),
            "post_ee": float(b.std(ddof=1) / np.sqrt(len(b))) if len(b) > 1 else float("nan"),
        }

    d_tierra = salida["grupos"]["tierra"]["delta"]
    d_asfalto = salida["grupos"]["asfalto"]["delta"]
    salida["did"] = d_tierra - d_asfalto

    # error estándar del DiD: suma de varianzas de las cuatro medias
    vars_ = []
    for sup in ("tierra", "asfalto"):
        g = salida["grupos"][sup]
        vars_.append((g["pre_ee"] ** 2 + g["post_ee"] ** 2)
                     if not (np.isnan(g["pre_ee"]) or np.isnan(g["post_ee"])) else np.nan)
    salida["did_ee"] = float(np.sqrt(np.nansum(vars_))) if not all(np.isnan(vars_)) else float("nan")
    salida["did_t"] = (salida["did"] / salida["did_ee"]
                       if salida["did_ee"] and not np.isnan(salida["did_ee"]) else float("nan"))
    return salida
