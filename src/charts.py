"""Figuras del análisis. Cada función devuelve la ruta del PNG que escribe."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

COLORES = {"tierra": "#8c6d3f", "asfalto": "#2b2b2b", "nieve": "#4a90c2", "mixto": "#b0b0b0"}
SALIDA = Path("reports/figures")


def _guardar(fig, nombre: str) -> Path:
    SALIDA.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA / nombre
    fig.savefig(ruta, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return ruta


def serie_temporal(df: pd.DataFrame) -> Path:
    """Velocidad media del ganador, rally por rally, 1973–2026."""
    fig, ax = plt.subplots(figsize=(11, 5.5))
    for sup in ["tierra", "asfalto", "nieve"]:
        d = df[df["superficie"] == sup]
        ax.scatter(d["anio"], d["vel_kmh"], s=16, alpha=0.55,
                   color=COLORES[sup], label=sup, edgecolors="none")
        if len(d) > 10:
            media = d.groupby("anio")["vel_kmh"].mean()
            ax.plot(media.index, media.values, color=COLORES[sup], lw=2, alpha=0.9)
    ax.axvline(1981, color="#c0392b", ls="--", lw=1.6)
    ax.text(1981.6, ax.get_ylim()[1] * 0.97, "1981: debut del 4WD\n(Audi Quattro)",
            color="#c0392b", fontsize=9, va="top")
    ax.set_xlabel("Año")
    ax.set_ylabel("Velocidad media del ganador (km/h)")
    ax.set_title("Velocidad media en el WRC, 1973–2026\nCada punto es un rally; la línea es la media del año")
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=0.25)
    return _guardar(fig, "01-serie-temporal.png")


def antes_despues_1981(df: pd.DataFrame) -> Path:
    """Media por superficie antes y después de 1981, con error estándar."""
    ventana = df[df["anio"].between(1975, 1987) & df["superficie"].isin(["tierra", "asfalto"])]
    fig, ax = plt.subplots(figsize=(8, 5))
    superficies = ["asfalto", "tierra"]
    x = np.arange(len(superficies))
    ancho = 0.36
    for i, (etiqueta, cond) in enumerate([
        ("1975–1980 (2WD)", ventana["anio"] <= 1980),
        ("1982–1987 (4WD)", ventana["anio"] >= 1982),
    ]):
        medias, errores = [], []
        for sup in superficies:
            d = ventana[(ventana["superficie"] == sup) & cond]["vel_kmh"]
            medias.append(d.mean() if len(d) else np.nan)
            errores.append(d.std() / np.sqrt(len(d)) if len(d) > 1 else 0)
        ax.bar(x + (i - 0.5) * ancho, medias, ancho, yerr=errores, capsize=4,
               label=etiqueta, color=["#9aa0a6", "#3d3d3d"][i], alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([s.capitalize() for s in superficies])
    ax.set_ylabel("Velocidad media del ganador (km/h)")
    ax.set_title("La misma comparación antes y después de la tracción total\nVentana 1975–1987, sólo rallys de una sola superficie")
    ax.legend(frameon=False)
    ax.grid(axis="y", alpha=0.25)
    return _guardar(fig, "02-antes-despues-1981.png")


def brecha_tierra_asfalto(df: pd.DataFrame) -> Path:
    """Diferencia tierra − asfalto por año: el indicador del efecto 4WD."""
    d = df[df["superficie"].isin(["tierra", "asfalto"])]
    tabla = (d.groupby(["anio", "superficie"])["vel_kmh"].mean()
              .unstack("superficie").dropna())
    if "tierra" not in tabla or "asfalto" not in tabla:
        return _guardar(plt.subplots(figsize=(8, 4))[0], "03-brecha.png")
    brecha = (tabla["tierra"] - tabla["asfalto"]).dropna()
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.axhline(0, color="black", lw=0.8)
    ax.bar(brecha.index, brecha.values, color="#8c6d3f", alpha=0.85)
    ax.axvline(1981, color="#c0392b", ls="--", lw=1.6)
    ax.set_xlabel("Año")
    ax.set_ylabel("Tierra − asfalto (km/h)")
    ax.set_title("Brecha de velocidad entre tierra y asfalto\nNegativo = la tierra es más lenta; se cierra si el 4WD ayuda más en superficie suelta")
    ax.grid(axis="y", alpha=0.25)
    return _guardar(fig, "03-brecha-superficie.png")


def distancia_por_anio(df: pd.DataFrame) -> Path:
    """La distancia de los rallys cambió mucho: hay que mostrarlo, porque
    condiciona cualquier comparación de velocidad."""
    fig, ax = plt.subplots(figsize=(11, 4.5))
    ax.scatter(df["anio"], df["distancia_tramos_km"], s=14, alpha=0.45, color="#444", edgecolors="none")
    media = df.groupby("anio")["distancia_tramos_km"].mean()
    ax.plot(media.index, media.values, color="#c0392b", lw=2)
    ax.set_xlabel("Año")
    ax.set_ylabel("Distancia de tramos cronometrados (km)")
    ax.set_title("Los rallys se acortaron: distancia total de tramos por rally")
    ax.grid(alpha=0.25)
    return _guardar(fig, "04-distancia.png")


def velocidad_vs_distancia(df: pd.DataFrame) -> Path:
    """Control: si la velocidad dependiera sólo de la longitud, se vería aquí."""
    fig, ax = plt.subplots(figsize=(8, 5))
    for sup in ["tierra", "asfalto", "nieve"]:
        d = df[df["superficie"] == sup]
        ax.scatter(d["distancia_tramos_km"], d["vel_kmh"], s=16, alpha=0.5,
                   color=COLORES[sup], label=sup, edgecolors="none")
    ax.set_xlabel("Distancia de tramos (km)")
    ax.set_ylabel("Velocidad media (km/h)")
    ax.set_title("Velocidad frente a longitud del rally\nSi la nube no tiene pendiente, la longitud no explica la velocidad")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    return _guardar(fig, "05-velocidad-vs-distancia.png")


def todas(df: pd.DataFrame) -> list[Path]:
    return [
        serie_temporal(df),
        antes_despues_1981(df),
        brecha_tierra_asfalto(df),
        distancia_por_anio(df),
        velocidad_vs_distancia(df),
    ]
