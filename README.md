# Tarea 2: resiliencia de la red de fibra óptica chilena ante el terremoto del 27F

Curso CIT3435 (UDP). A partir del archivo de infraestructura entregado por SUBTEL (basado en el Estudio de NIC Chile), el repositorio
construye la topología de red con `pgr_createTopology`, define 24 nodos clave, carga el sismo 8,8 desde USGS, calcula la probabilidad de falla
de cada enlace con un modelo de atenuación y de tasa de cortes, y obtiene el ATTR (confiabilidad promedio entre pares) antes y después del
terremoto. El informe está en `main.tex` (IEEEtran).

## Cómo ejecutarlo (un solo comando)

Requisitos: **Docker con el plugin `docker compose` v2**, Python 3.10 o superior (solo para lanzar `main.py`, que usa únicamente la biblioteca
estándar) y los puertos 5433 y 8000 libres. Funciona en Linux, macOS y Windows con Docker Desktop. No hay que instalar PostgreSQL ni PostGIS.

```bash
git clone https://github.com/benjamin09111/tarea2-resiliencia.git
cd tarea2-resiliencia
python3 main.py
```

La primera ejecución descarga la imagen de la base de datos (`pgrouting/pgrouting:16-3.5-3.8.0`) y construye el contenedor Python; las siguientes
tardan cerca de 1,5 minutos. `python3 main.py` hace, en este orden:

1. Comprueba Docker y levanta PostgreSQL 16 + PostGIS 3.5 + pgRouting 3.8.0.
2. Crea una base de datos **vacía** y carga `main.sql` (infraestructura, topología, nodos clave, sismo y probabilidades de falla).
3. Topología: ejecuta `pgr_createTopology` (tolerancia 0,0001°) sobre una copia y compara su estructura con la de `main.sql`.
4. Sismo: carga el GeoJSON del USGS (`datos/crudos/usgs_official20100227063411530_30.geojson`) en la tabla `sismo`.
5. Probabilidades: recalcula la probabilidad de falla de cada enlace (`sql/05_probabilidades.sql`) y verifica que coincide con `main.sql`.
6. ATTR **antes** (operación, exacto) y **después** del terremoto (Monte Carlo, N = 10.000, semilla 20100227) para dos redes, RF y RE, e imprime la tabla.
7. Genera el mapa Leaflet (`mapa/index.html`) y lo sirve en **http://localhost:8000/mapa/**.

Salida esperada del paso 6 (el programa imprime cuatro decimales y avisa si no coinciden con el informe, que los redondea a tres):

| Red | ATTR en operación | ATTR tras el terremoto (IC 95 %) | Diferencia | Variación |
|---|---|---|---|---|
| RF (fibra detectada + acometidas) | 0,2174 | 0,1324 (0,1314–0,1334) | −0,0850 | −39,1 % |
| RE (las 4 capas + acometidas) | 1,0000 | 0,3141 (0,3126–0,3157) | −0,6859 | −68,6 % |

Opciones: `--desde-cero` reconstruye todo desde los shapefiles SAIP y reescribe `main.sql` (1 minuto); `--sin-mapa` omite el mapa; `--bajar` apaga
los contenedores y borra la base de datos.

## Escenarios y supuestos

- **RF**: solo la fibra detectada (10.312,8 km) más las acometidas. **RE**: además postación, caminos y ferry, que no son fibra verificada.
- Los enlaces de postación, caminos, ferry y las **acometidas** (segmentos rectos de cada nodo clave a la fibra situada a menos de 20 km) son
  **sintéticos**: están marcados en `red_noded.sintetico` y se dibujan en trazo discontinuo en el mapa.
- En operación todos los enlaces tienen probabilidad de falla 0 (la columna `prob_falla` parte en 0); tras el sismo se usa la probabilidad del modelo.
- El modelo y sus parámetros (con la fuente de cada uno) están en `config.json` y en la tabla `parametros_modelo`.

## Dependencias y para qué se usan

| Dependencia | Uso |
|---|---|
| Docker Compose + imagen `pgrouting/pgrouting:16-3.5-3.8.0` | base de datos con PostGIS y pgRouting 3.8.0 (última con `pgr_createTopology`, obsoleta en esa versión) |
| `psycopg` | conexión a PostgreSQL desde Python |
| `pyshp` | lectura de los shapefiles SAIP (solo en `--desde-cero`) |
| `numpy`, `scipy` | Monte Carlo y componentes conexas (`scipy.sparse.csgraph`) |
| `networkx` | puentes del grafo para los corredores críticos |
| `folium` | genera el mapa Leaflet |
| `matplotlib` | figuras del informe (`src/figuras.py`, no forma parte del flujo de `main.py`) |

Las versiones exactas están fijadas en `requirements.txt`. El mapa usa teselas de Esri y las librerías Leaflet desde CDN, por lo que necesita internet para verse completo.

## Estructura

```
main.py            orquestador (un solo comando)          main.sql     base de datos completa (pg_dump)
config.json        parámetros del modelo, ATTR y datos     docker-compose.yml, Dockerfile, requirements.txt
sql/               00 esquema · 01 nodado · 02 topología · 03 componentes/conectividad · 04 modelo · 05 probabilidades · 06 controles
src/               cargar_saip · topologia (barrido) · nodos_clave · cargar_sismo · probabilidades · attr · analisis · sensibilidad · mapa · figuras
datos/             crudos/saip_T5610 (shapefiles SAIP), crudos/usgs_*.geojson, nodos_clave.csv
resultados/        salidas de cada fase (la evidencia de las cifras del informe)      mapa/index.html   mapa Leaflet
figuras/           figuras del informe       main.tex, referencias.bib   informe      plan_maestro.md, contexto/   plan y bitácora
```

## Fuentes de datos

Archivo SAIP AN002T0005610 (carta SUBTEL ORD. 7479/G, 2023, derivado del Estudio de NIC Chile 2018); evento USGS `official20100227063411530_30`
(<https://earthquake.usgs.gov/fdsnws/event/1/query?eventid=official20100227063411530_30&format=geojson>); instalaciones de PeeringDB y puntos de
aterrizaje de submarinecablemap (ver `datos/nodos_clave.csv`, que lista la fuente de cada nodo). Parámetros del modelo: Saragoni, Astroza y Ruiz (2004), Tabla 1, ec. (2),
e Isoyama et al. (2000), ec. (5) y Tabla 3.

## Problemas frecuentes

- *Puerto 5433 u 8000 ocupado*: cambiar el puerto del anfitrión en `docker-compose.yml`.
- *`permission denied` con Docker en Linux*: `sudo usermod -aG docker $USER` y volver a iniciar sesión.
- *`mapa/index.html` aparece modificado en git tras ejecutar*: folium escribe identificadores aleatorios; el contenido del mapa es el mismo.
- *Compilar el informe*: `latexmk -pdf main.tex` o `pdflatex main.tex` dos veces (TeX Live con `IEEEtran`, `babel-spanish` y `siunitx`). La bibliografía está incluida dentro de `main.tex`, así que solo se necesitan ese archivo y la carpeta `figuras/` (también sirve en Overleaf con pdfLaTeX). `referencias.bib` es la fuente de esas referencias.
