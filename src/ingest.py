"""Recolector del archivo WRC (juwra.com) — rally por rally, 1973 al presente.

Estructura del sitio (verificado el 23-nov-2026 contra 1973, 1976 y 2025):

    calendar_<año>.html        -> enlaces a los rallys de esa temporada
    <slug>_<año>.html          -> ficha del rally: superficie, distancias, participantes
    <slug>_<año>_results.html  -> clasificación final: Pos, Nr, Driver/Car, Nat, Gr, Time

La ficha es la fuente principal porque publica la superficie de forma explícita
("Surface: Snow"), así que no hay que clasificarla a mano. De la clasificación se
toma sólo la primera fila: ganador y tiempo total.

Uso:
    python -m src.ingest --desde 1973 --hasta 2026

Escribe data/rallys.csv. Es idempotente: salta los rallys que ya están en el CSV,
así que se puede cortar y retomar.
"""

from __future__ import annotations

import argparse
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE = "https://www.juwra.com"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

CAMPOS = [
    "anio", "slug", "rally", "superficie", "distancia_tramos_km",
    "distancia_total_km", "inscritos", "finalizados", "tramos",
    "ganador", "auto", "tiempo_s", "url",
]

NO_SON_RALLY = {
    "season", "teams", "rules", "calendar", "statistics", "people", "rallies",
    "sitemap", "index", "help", "legal", "copyright", "preseason_roundup",
    "championship", "standings", "result_compilation",
}

SUPERFICIES = {"gravel": "tierra", "asphalt": "asfalto", "snow": "nieve",
               "mixed": "mixto", "tarmac": "asfalto", "ice": "nieve"}


def _get(url: str, reintentos: int = 3) -> str | None:
    """GET con reintentos. None si el recurso no existe (404)."""
    for intento in range(reintentos):
        try:
            r = requests.get(url, headers={"User-Agent": UA}, timeout=30)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            r.encoding = "ISO-8859-1"
            return r.text
        except requests.RequestException:
            if intento == reintentos - 1:
                return None
            time.sleep(1.5 * (intento + 1))
    return None


def _texto(html: str) -> str:
    """Texto plano normalizado: sin etiquetas, sin &nbsp;, espacios colapsados."""
    t = BeautifulSoup(html, "lxml").get_text(" | ", strip=True)
    return re.sub(r"\s+", " ", t.replace("\xa0", " "))


def rallys_de_temporada(anio: int) -> list[tuple[str, str]]:
    """[(slug, nombre)] de un año, en orden de calendario."""
    html = _get(f"{BASE}/calendar_{anio}.html")
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    vistos: dict[str, str] = {}
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.endswith(f"_{anio}.html"):
            continue
        if any(s in href for s in ("_itinerary", "_results", "_entries")):
            continue
        slug = href[: -len(f"_{anio}.html")]
        if slug in NO_SON_RALLY:
            continue
        nombre = a.get_text(" ", strip=True) or slug.replace("_", " ").title()
        if slug not in vistos and nombre:
            vistos[slug] = nombre
    return list(vistos.items())


def _num(txt: str) -> float | None:
    """Número con separador de miles opcional: '1,661.00' -> 1661.0"""
    m = re.search(r"([0-9][0-9,]*(?:\.[0-9]+)?)", txt)
    if not m:
        return None
    return float(m.group(1).replace(",", ""))


NUM = r"([0-9][0-9,]*(?:\.[0-9]+)?)"


def ficha_rally(html: str) -> dict:
    """Extrae superficie, distancias y participantes de la ficha del rally.

    La ficha es una tabla de pares etiqueta/valor. Se busca por etiqueta y se
    toma el valor siguiente, que es lo robusto frente a cambios de maquetación.
    """
    t = _texto(html)
    datos: dict = {}

    m = re.search(r"Official name: \| ([^|]+)", t)
    datos["rally"] = m.group(1).strip() if m else None

    m = re.search(r"Surface: \| ([A-Za-z ]+)", t)
    if m:
        crudo = m.group(1).strip().lower()
        datos["superficie"] = SUPERFICIES.get(crudo, crudo)

    m = re.search(r"Actual stage distance: \| " + NUM, t)
    if not m:
        m = re.search(r"Planned stage distance: \| " + NUM, t)
    datos["distancia_tramos_km"] = _num(m.group(1)) if m else None

    m = re.search(r"Total distance: \| " + NUM, t)
    datos["distancia_total_km"] = _num(m.group(1)) if m else None

    for campo, etiqueta in (("inscritos", "Entries"), ("finalizados", "Finishers")):
        m = re.search(rf"{etiqueta}: \| " + NUM, t)
        datos[campo] = int(_num(m.group(1))) if m else None

    m = re.search(r"Stages: \| " + NUM, t)
    datos["tramos"] = int(_num(m.group(1))) if m else None
    return datos


def tiempo_a_segundos(texto: str) -> int | None:
    """'2h 21m 51,4s' -> 8511. El archivo usa coma decimal."""
    t = texto.strip().replace(",", ".")
    h = re.search(r"(\d+)\s*h", t)
    m = re.search(r"(\d+)\s*m", t)
    s = re.search(r"(\d+(?:\.\d+)?)\s*s", t)
    if not (h or m or s):
        return None
    total = 0.0
    if h:
        total += int(h.group(1)) * 3600
    if m:
        total += int(m.group(1)) * 60
    if s:
        total += float(s.group(1))
    return int(round(total)) if total > 60 else None


MARCAS = ("Toyota", "Ford", "Hyundai", "Skoda", "Citroen", "Peugeot", "Renault",
          "Lancia", "Audi", "Subaru", "Mitsubishi", "Mini", "Fiat", "Opel",
          "Alpine", "Datsun", "Volkswagen", "Seat", "MG", "Saab", "Porsche",
          "BMW", "Mercedes", "Ferrari", "Alfa", "Abarth", "Talbot", "Vauxhall",
          "Triumph", "Volvo", "Nissan", "Mazda", "Honda", "Suzuki", "Chrysler",
          "Wartburg", "Trabant", "Lada", "Moskvich", "Zastava", "Polski", "Dacia",
          "Simca", "Innocenti", "Autobianchi", "Austin", "Morris", "Sunbeam")


def ganador(html: str) -> tuple[str, str, int] | None:
    """Primera fila de la clasificación final: (piloto, auto, segundos)."""
    soup = BeautifulSoup(html, "lxml")
    patron_marca = "|".join(MARCAS)
    for tabla in soup.find_all("table"):
        filas = tabla.find_all("tr")
        if not 4 < len(filas) < 400:
            continue
        for fila in filas:
            celdas = [c.get_text(" ", strip=True) for c in fila.find_all(["td", "th"])]
            celdas = [c for c in celdas if c]
            if len(celdas) < 4:
                continue
            if not re.match(r"^1(st)?$", celdas[0]):
                continue
            resto = celdas[1:]
            piloto_auto = next(
                (c for c in resto if re.search(patron_marca, c) and len(c) > 6), None)
            if not piloto_auto:
                continue
            segundos = next(
                (v for c in resto if (v := tiempo_a_segundos(c))), None)
            if not segundos:
                continue
            m = re.match(rf"^(.*?)((?:{patron_marca}).*)$", piloto_auto)
            if m:
                piloto, auto = m.group(1).strip(" ,"), m.group(2).strip()
            else:
                partes = piloto_auto.split(",", 1)
                piloto, auto = partes[0].strip(), ""
            piloto = re.sub(r"\s*\(.*\)$", "", piloto).strip()
            return piloto, auto, segundos
    return None


def recolectar(desde: int, hasta: int, salida: Path) -> None:
    hecho: set[tuple[int, str]] = set()
    if salida.exists():
        with salida.open(newline="", encoding="utf-8") as f:
            for fila in csv.DictReader(f):
                if fila.get("anio"):
                    hecho.add((int(fila["anio"]), fila["slug"]))
        print(f"  ya recolectados: {len(hecho)} rallys")

    nuevo = not salida.exists()
    with salida.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if nuevo:
            w.writeheader()

        for anio in range(desde, hasta + 1):
            rallys = rallys_de_temporada(anio)
            if not rallys:
                print(f"  {anio}: sin calendario", flush=True)
                continue
            filas = 0
            for slug, nombre in rallys:
                if (anio, slug) in hecho:
                    continue
                html = _get(f"{BASE}/{slug}_{anio}.html")
                if not html:
                    continue
                d = ficha_rally(html)
                if not d.get("distancia_tramos_km"):
                    continue
                html_res = _get(f"{BASE}/{slug}_{anio}_results.html")
                if not html_res:
                    continue
                g = ganador(html_res)
                if not g:
                    continue
                piloto, auto, seg = g
                w.writerow({
                    "anio": anio, "slug": slug, "rally": d.get("rally") or nombre,
                    "superficie": d.get("superficie"),
                    "distancia_tramos_km": d.get("distancia_tramos_km"),
                    "distancia_total_km": d.get("distancia_total_km"),
                    "inscritos": d.get("inscritos"), "finalizados": d.get("finalizados"),
                    "tramos": d.get("tramos"),
                    "ganador": piloto, "auto": auto, "tiempo_s": seg,
                    "url": f"{BASE}/{slug}_{anio}.html",
                })
                f.flush()
                filas += 1
                time.sleep(0.25)
            print(f"  {anio}: {filas}/{len(rallys)}", flush=True)


def main() -> None:
    p = argparse.ArgumentParser(description="Recolecta rallys del archivo WRC")
    p.add_argument("--desde", type=int, default=1973)
    p.add_argument("--hasta", type=int, default=2026)
    p.add_argument("--salida", type=Path, default=Path("data/rallys.csv"))
    a = p.parse_args()
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    recolectar(a.desde, a.hasta, a.salida)


if __name__ == "__main__":
    main()
