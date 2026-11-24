"""Pipeline del análisis: carga, limpia, contrasta y dibuja.

Uso:
    python run_analysis.py
    python run_analysis.py --csv data/rallys.csv --sin-figuras

Imprime el resultado y lo deja en reports/resultados.json para que el README no
tenga ni una cifra escrita a mano.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from src import charts, metrics


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--csv", type=Path, default=Path("data/rallys.csv"))
    p.add_argument("--sin-figuras", action="store_true")
    a = p.parse_args()

    crudo = pd.read_csv(a.csv)
    print(f"Filas leídas: {len(crudo)}")
    print(f"Rango: {crudo.anio.min()}–{crudo.anio.max()}\n")

    df = metrics.limpiar(crudo)
    print(f"Tras limpieza: {len(df)} filas")
    for motivo, n in df.attrs.get("motivos", {}).items():
        print(f"  descartadas por {motivo}: {n}")
    print()

    # --- panorama general -------------------------------------------------
    print("=" * 62)
    print("VELOCIDAD MEDIA DEL GANADOR POR DÉCADA")
    print("=" * 62)
    dec = metrics.resumen_por_decada(df)
    for _, r in dec.iterrows():
        print(f"  {int(r.decada)}s  {r.superficie:<8} "
              f"{r.vel_media:6.1f} km/h  (n={int(r.n):3d}, ±{r.ee:.1f})")

    print()
    print("=" * 62)
    print("CONTRASTE 1981 — DIFERENCIA EN DIFERENCIAS")
    print("=" * 62)
    c = metrics.contraste_1981(df)
    for sup, g in c["grupos"].items():
        print(f"  {sup:<8} 1975-80: {g['pre_media']:6.2f} (n={g['pre_n']:2d})"
              f"  1982-87: {g['post_media']:6.2f} (n={g['post_n']:2d})"
              f"  Δ = {g['delta']:+.2f} km/h")
    print(f"\n  DiD (tierra − asfalto) = {c['did']:+.2f} km/h")
    print(f"  error estándar          = {c['did_ee']:.2f}")
    print(f"  t = {c['did_t']:.2f}")

    # --- decadas extremas -------------------------------------------------
    primero = df[df.anio.between(1973, 1979)]["vel_kmh"].mean()
    ultimo = df[df.anio.between(2020, 2026)]["vel_kmh"].mean()
    print()
    print("=" * 62)
    print("DE 1973-1979 A 2020-2026")
    print("=" * 62)
    print(f"  media 1973-79: {primero:.1f} km/h")
    print(f"  media 2020-26: {ultimo:.1f} km/h")
    print(f"  diferencia:    {ultimo - primero:+.1f} km/h "
          f"({100 * (ultimo - primero) / primero:+.1f}%)")

    # --- control por distancia -------------------------------------------
    print()
    print("=" * 62)
    print("CONTROL POR LONGITUD (rallies de 250-400 km de tramos)")
    print("=" * 62)
    ctrl = metrics.control_por_distancia(df)
    for _, r in ctrl.iterrows():
        print(f"  {int(r.decada)}s: {r.vel_media:5.1f} km/h  (n={int(r.n)})")
    r_dist = df["distancia_tramos_km"].corr(df["vel_kmh"])
    d70 = ctrl[ctrl.decada == 1970]["vel_media"]
    d20 = ctrl[ctrl.decada == 2020]["vel_media"]
    delta_ctrl = float(d20.iloc[0] - d70.iloc[0]) if len(d70) and len(d20) else float("nan")
    print(f"\n  correlación distancia↔velocidad: {r_dist:+.3f}")
    print(f"  Δ 1970s→2020s con longitud fija: {delta_ctrl:+.1f} km/h")

    # --- por superficie ---------------------------------------------------
    print()
    print("=" * 62)
    print("POR SUPERFICIE: 1973-1979 vs 2020-2026")
    print("=" * 62)
    sup = metrics.resumen_por_superficie(df)
    for _, r in sup.iterrows():
        print(f"  {r.superficie:<8} {r.antes_media:6.1f} (n={r.antes_n:2d}) → "
              f"{r.despues_media:6.1f} (n={r.despues_n:2d})  Δ={r.delta:+6.1f} km/h")

    # --- fiabilidad -------------------------------------------------------
    fin = df.dropna(subset=["tasa_finish"])
    if len(fin) > 50:
        print()
        print("=" * 62)
        print("FIABILIDAD (porcentaje de inscritos que terminan)")
        print("=" * 62)
        for etiqueta, cond in [("1973-1990", fin.anio.between(1973, 1990)),
                               ("1991-2009", fin.anio.between(1991, 2009)),
                               ("2010-2026", fin.anio.between(2010, 2026))]:
            d = fin[cond]["tasa_finish"]
            if len(d):
                print(f"  {etiqueta}: {d.mean():5.1f}%  (n={len(d)})")

    # --- figuras ----------------------------------------------------------
    rutas = []
    if not a.sin_figuras:
        rutas = [str(r) for r in charts.todas(df)]
        print()
        print("Figuras:")
        for r in rutas:
            print("  ", r)

    salida = {
        "filas_crudas": int(len(crudo)),
        "filas_limpias": int(len(df)),
        "descartadas": df.attrs.get("descartados", 0),
        "motivos": df.attrs.get("motivos", {}),
        "rango_anios": [int(crudo.anio.min()), int(crudo.anio.max())],
        "media_1973_1979": round(float(primero), 2),
        "media_2020_2026": round(float(ultimo), 2),
        "delta_total": round(float(ultimo - primero), 2),
        "contraste_1981": {
            "did": round(c["did"], 3),
            "did_ee": round(c["did_ee"], 3),
            "did_t": round(c["did_t"], 2),
            "grupos": {k: {kk: (round(vv, 3) if isinstance(vv, float) else vv)
                           for kk, vv in v.items()} for k, v in c["grupos"].items()},
        },
        "por_decada": [
            {"decada": int(r.decada), "superficie": r.superficie,
             "vel_media": round(float(r.vel_media), 2), "n": int(r.n)}
            for _, r in dec.iterrows()
        ],
        "control_longitud": {
            "correlacion_distancia_velocidad": round(float(r_dist), 3),
            "delta_1970s_2020s": round(delta_ctrl, 2),
            "por_decada": [
                {"decada": int(r.decada), "vel_media": round(float(r.vel_media), 2),
                 "n": int(r.n)} for _, r in ctrl.iterrows()
            ],
        },
        "por_superficie": [
            {"superficie": r.superficie, "antes": round(float(r.antes_media), 2),
             "antes_n": int(r.antes_n), "despues": round(float(r.despues_media), 2),
             "despues_n": int(r.despues_n), "delta": round(float(r.delta), 2)}
            for _, r in sup.iterrows()
        ],
        "fiabilidad": {
            "1973-1990": round(float(fin[fin.anio.between(1973, 1990)]["tasa_finish"].mean()), 1),
            "1991-2009": round(float(fin[fin.anio.between(1991, 2009)]["tasa_finish"].mean()), 1),
            "2010-2026": round(float(fin[fin.anio.between(2010, 2026)]["tasa_finish"].mean()), 1),
        },
        "figuras": rutas,
    }
    Path("reports").mkdir(exist_ok=True)
    Path("reports/resultados.json").write_text(
        json.dumps(salida, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nGuardado reports/resultados.json")


if __name__ == "__main__":
    main()
