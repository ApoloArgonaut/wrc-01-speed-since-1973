# ¿Cuánto más rápido es un rally que hace 50 años?

**+19.9 km/h. Y sólo +16.5 cuando se controla por lo que de verdad cambió: los rallys miden hoy la mitad.**

![Velocidad media del ganador en el WRC, 1973–2026](reports/figures/01-serie-temporal.png)

---

## El resultado

El ganador de un rally del WRC promedia **101.1 km/h entre 2020 y 2026**. Entre 1973
y 1979 promediaba **81.2 km/h**.

Son **+19.9 km/h en cincuenta años**, un 24.6% más rápido.

Pero esa cifra sola engaña, y el análisis lo demuestra con el mismo dato: los rallys
pasaron de **574 km de tramos cronometrados en los años 70 a 298 km en la década de
2020**. La longitud correlaciona negativamente con la velocidad media
(**Pearson −0.37**): un recorrido largo incluye tramos rotos, enlaces y promedio más
bajo.

Restringiendo la comparación a rallys de longitud parecida (250–400 km de tramos), la
mejora real es de **+16.5 km/h**, no de +19.9.

Esa diferencia de 3.4 km/h es el hallazgo del proyecto.

---

## Por qué importa

La pregunta "¿son más rápidos los rallies?" se contesta con un gráfico. La pregunta que
importa es *cuánto de ese aumento es el coche y cuánto es el recorrido*, porque el
recorrido no lo cambió la ingeniería: lo cambió el reglamento.

Sin separarlo, cualquier conclusión sobre la evolución técnica del rally está
contaminada.

---

## De dónde salen los datos

`juwra.com`, archivo independiente del WRC, 1973 al presente. Sin API, sin
credenciales.

```
calendar_<año>.html          → rallys de la temporada
<slug>_<año>.html            → superficie, distancia de tramos, inscritos, finalizados
<slug>_<año>_results.html    → ganador y tiempo total
```

**633 rallys recolectados** de los 682 que aparecen en los calendarios: 93% de
cobertura. El resto no publica la distancia cronometrada.

De cada rally se guarda el mínimo verificable: superficie, distancia cronometrada y
tiempo del ganador. La velocidad media es **distancia entre tiempo**, sin ningún
ajuste.

La superficie no se clasificó a mano: la publica el archivo en la ficha de cada rally
(`Surface: Gravel / Asphalt / Snow`) y se usa tal cual.

---

## Cómo se corre

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m src.ingest --desde 1973 --hasta 2026   # ~15 min, idempotente
.venv/bin/python run_analysis.py                           # figuras + resultados.json
```

| Archivo | Qué hace |
|---|---|
| `src/ingest.py` | Recolecta los rallys. Idempotente: se puede cortar y retomar |
| `src/metrics.py` | Velocidad, tasa de finalización, control por longitud |
| `src/charts.py` | La figura y las de contraste |
| `run_analysis.py` | Pipeline completo; escribe `reports/resultados.json` |

---

## Control de calidad

De 633 rallys, **609 pasan el filtro**. Los 24 descartados quedan registrados con su
motivo:

```
distancia_imposible    19   (menos de 50 km o más de 1200 km de tramos)
velocidad_imposible     5   (fuera del rango físico 40–160 km/h)
```

Ninguna fila se corrigió a mano: se descarta y se reporta el descarte.

---

## Limitaciones

1. **Un solo dato por rally: el ganador.** No hay información por coche, neumático ni
   condiciones. Todo lo que se afirma es sobre el ganador, no sobre la parrilla.
2. **La velocidad media depende del trazado.** Un rally rápido puede serlo porque su
   recorrido es rápido. El control por longitud reduce el problema, no lo elimina.
3. **La composición del calendario cambió.** En 1973 había rallys de 1,258 km de
   tramos (Marruecos); hoy el más largo no llega a 400. Comparar épocas compara
   calendarios distintos.
4. **Se excluyeron los rallys maratón.** Costa de Marfil (1976–1985) tuvo entre 4,000 y
   5,622 km cronometrados sin tramos: el recorrido entero contaba. Son datos reales,
   no errores, pero no miden lo mismo.
5. **Cobertura del 93%.**

## Lo que no se puede afirmar con estos datos

- Que las mejoras técnicas causaran el aumento. Este análisis mide cuánto cambió la
  velocidad, no por qué.
- Que los coches de hoy sean "mejores" que los de 1973. Se mide velocidad media del
  ganador en un rally, que es otra cosa.

---

## Fuente

`juwra.com` — archivo independiente del WRC, mantenido por Jonkka. No es un sitio
oficial de la FIA. Cada fila del dataset guarda la URL del rally del que salió.

Código MIT. Los datos pertenecen a su fuente.
