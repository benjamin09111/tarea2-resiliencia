# Tarea 2: resiliencia de la red de fibra óptica chilena ante el terremoto del 27F

Curso CIT3435 (UDP). Este repositorio contiene **todo** el trabajo: el código, los datos, los resultados, el mapa y el informe.

## 1. Qué hace este trabajo (en 5 líneas)

1. Toma la infraestructura chilena entregada por SUBTEL (archivo SAIP, basado en el Estudio de NIC Chile) y la convierte en una **red** (nodos y enlaces) con `pgr_createTopology`.
2. Define **24 nodos clave** (puntos que generan, intercambian o reciben información: data centers, puntos de intercambio, aterrizajes de cables, capitales regionales).
3. Descarga el **terremoto 8,8 del 27F** desde USGS y lo carga en la base de datos.
4. Calcula la **probabilidad de que falle cada enlace** según su distancia al epicentro (un modelo de la literatura).
5. Calcula el **ATTR** (confiabilidad promedio entre pares de nodos clave) **antes y después** del terremoto, y dibuja todo en un **mapa Leaflet**.

## 2. Qué contiene el repositorio

| Archivo o carpeta | Qué hay |
|---|---|
| `main.pdf` / `main.tex` | **El informe** (paper en formato IEEE). `main.tex` es el código fuente. |
| `main.py` | **El programa principal**: ejecuta todo con un solo comando. |
| `main.sql` | La **base de datos completa** (red, nodos, sismo y probabilidades de falla ya calculadas). |
| `mapa/index.html` | El **mapa Leaflet** (se abre en el navegador). |
| `resultados/` | La **evidencia**: la salida de cada paso (cada cifra del informe sale de aquí). |
| `datos/` | Datos de entrada: los shapefiles SAIP, el GeoJSON del terremoto (USGS) y la lista de nodos clave. |
| `sql/` | Los scripts SQL (topología, modelo de falla, probabilidades). |
| `src/` | Los scripts Python (carga de datos, ATTR, mapa, etc.). |
| `figuras/` | Las imágenes del informe. |
| `config.json` | Los parámetros del modelo, en un solo lugar. |
| `docker-compose.yml`, `Dockerfile`, `requirements.txt` | Lo necesario para que todo corra igual en cualquier computador. |
| `referencias.bib` | Bibliografía del informe. |

## 3. Cómo usarlo, paso a paso

### Lo único que hay que tener instalado
- **Docker** con el comando `docker compose` (versión 2). En Windows o Mac sirve Docker Desktop.
- **Python 3.10 o superior** (solo para lanzar `main.py`; no hay que instalar librerías).
- Los puertos **5433** y **8000** libres.

No hay que instalar PostgreSQL, PostGIS ni nada más: todo corre dentro de Docker.

### Paso 1. Descargar el repositorio
```bash
git clone https://github.com/benjamin09111/tarea2-resiliencia.git
cd tarea2-resiliencia
```

### Paso 2. Ejecutar todo con un solo comando
```bash
python3 main.py
```
La **primera vez** tarda unos minutos, porque Docker descarga la imagen de la base de datos. Las siguientes veces tarda **cerca de 1 minuto**.

### Paso 3. Leer lo que muestra en pantalla
El programa imprime 8 pasos numerados. Al final aparece esta tabla, que **debe coincidir con el informe**:

| Red | ATTR en operación | ATTR tras el terremoto (IC 95 %) | Diferencia | Variación |
|---|---|---|---|---|
| RF (solo la fibra detectada, más acometidas) | 0,2174 | 0,1324 (0,1314–0,1334) | −0,0850 | −39,1 % |
| RE (las 4 capas, más acometidas) | 1,0000 | 0,3141 (0,3126–0,3157) | −0,6859 | −68,6 % |

Si todo salió bien verá tres mensajes `OK` (topología, probabilidades y valores del informe). El programa imprime 4 decimales; el informe los redondea a 3.

### Paso 4. Ver el mapa
Abra en el navegador **http://localhost:8000/mapa/** (o abra directamente `mapa/index.html`; necesita internet para cargar el mapa base). En el mapa se ve:
- la **fibra** coloreada de amarillo a rojo según su probabilidad de falla (gris: sin daño);
- los enlaces **sintéticos** (postes, caminos, ferry y acometidas) en líneas discontinuas;
- los **24 nodos clave** (verde: genera, naranja: intercambia, azul: recibe);
- el **epicentro** (estrella roja) y círculos de aceleración del terremoto;
- un recuadro con los dos ATTR. Al hacer clic en un nodo o pasar el cursor sobre un enlace, se ve su detalle.

### Paso 5. Apagar todo
```bash
python3 main.py --bajar
```
Apaga los contenedores y borra la base de datos.

### Otras opciones de `main.py`
- `python3 main.py --sin-mapa`: ejecuta todo menos el mapa.
- `python3 main.py --desde-cero`: reconstruye todo **desde los archivos originales** (shapefiles) y vuelve a escribir `main.sql` (demora cerca de 1 minuto).

## 4. Qué hace `main.py`, paso a paso

| Paso | Qué hace | Dónde está el código |
|---|---|---|
| 1 | Comprueba que Docker funcione. | `main.py` |
| 2 | Levanta la base de datos (PostgreSQL + PostGIS + pgRouting). | `docker-compose.yml` |
| 3 | Crea una base de datos **vacía** y carga `main.sql`. | `main.sql` |
| 4 | **Topología**: vuelve a ejecutar `pgr_createTopology` sobre una copia y comprueba que da la misma red. | `sql/02_red_noded.sql` |
| 5 | **Terremoto**: carga el GeoJSON de USGS en la tabla `sismo`. | `src/cargar_sismo.py` |
| 6 | **Probabilidades de falla**: recalcula la probabilidad de cada enlace y comprueba que coincide con `main.sql`. | `sql/04_modelo_falla.sql`, `sql/05_probabilidades.sql`, `src/probabilidades.py` |
| 7 | **ATTR antes y después** del terremoto; imprime la tabla. | `src/attr.py` |
| 8 | **Mapa**: genera `mapa/index.html` y lo publica en el puerto 8000. | `src/mapa.py` |

## 5. Dónde está cada parte de la tarea

| Lo que pide la tarea | Dónde verlo |
|---|---|
| Descargar la infraestructura y cargarla | `datos/crudos/saip_T5610/` y `src/cargar_saip.py`; inventario en `resultados/01_inventario.txt` |
| Identificar los nodos clave | `datos/nodos_clave.csv` (24 nodos con rol, coordenadas, fuente y justificación) y `src/nodos_clave.py` |
| Topología con `pgr_createTopology` | `sql/01_nodar.sql`, `sql/02_red_noded.sql`; evidencia en `resultados/02_*` |
| Script que calcula el ATTR | `src/attr.py` |
| ATTR en operación | `resultados/04_attr_operacion.txt` (y `attr.json`) |
| Sismo 8,8 en GeoJSON, cargado en la BD | `datos/crudos/usgs_official20100227063411530_30.geojson`, `src/cargar_sismo.py`, `resultados/05_sismo.txt` |
| Modelo de falla probabilístico y su fuente | `config.json` (parámetros) y el informe (sección V-C); fuentes: Saragoni et al. (2004) e Isoyama et al. (2000) |
| Script que calcula la probabilidad de cada enlace | `sql/05_probabilidades.sql` y `src/probabilidades.py`; resultados en `resultados/06_*` |
| Archivo `main.sql` con las probabilidades | `main.sql` (prueba de carga en una base vacía: `resultados/07_carga_main_sql.txt`) |
| Nuevo ATTR tras el terremoto | `resultados/08_attr_terremoto.txt` y el informe (sección VI-C) |
| `main.py` + mapa Leaflet + ATTR antes y después | `main.py` y `mapa/index.html` |

## 6. Conceptos que conviene conocer

- **ATTR** (*average two-terminal reliability*): de todos los pares posibles de nodos clave (24 nodos dan 276 pares), la fracción que sigue conectada. Vale 1 si todos se pueden comunicar y 0 si ninguno.
- **RF y RE**: dos versiones de la red. **RF** usa solo la fibra detectada en el archivo SAIP (10.312,8 km). **RE** agrega además postes, caminos y ferry, que son rutas donde no se verificó fibra.
- **Enlace sintético**: un enlace que no viene en los datos de fibra (postes, caminos, ferry y *acometidas*). Está marcado con `sintetico = true`.
- **Acometida**: un segmento recto que une cada nodo clave con la fibra más cercana (hasta 20 km). Se agrega porque el archivo SAIP no incluye los anillos urbanos.
- **Probabilidad de falla**: en operación vale 0 en todos los enlaces; tras el terremoto se calcula según qué tan fuerte fue la sacudida en cada enlace (columna `prob_falla`).

## 7. Cómo entender el código (orden de lectura sugerido)

1. `main.py`: el flujo completo, en funciones cortas con nombres claros (`desde_main_sql`, `attr_y_tabla`, `mapa`).
2. `config.json`: todos los parámetros (tolerancia de la topología, parámetros del modelo, número de simulaciones y semilla).
3. `src/cargar_saip.py` → `sql/01_nodar.sql` → `sql/02_red_noded.sql`: de los shapefiles a la red con topología.
4. `src/nodos_clave.py`: crea los nodos clave y las acometidas.
5. `sql/04_modelo_falla.sql` y `sql/05_probabilidades.sql`: la fórmula del modelo y su aplicación a cada enlace.
6. `src/attr.py`: el cálculo del ATTR (exacto en operación; simulación de Monte Carlo para el terremoto).
7. `src/mapa.py`: el mapa.

Resto de los scripts: `src/analisis.py` (nodos más afectados y corredores críticos), `src/sensibilidad.py` (qué pasa si cambian los supuestos), `src/topologia.py` (prueba con distintas tolerancias), `src/figuras.py` (figuras del informe) y `sql/06_controles.sql` (controles de las probabilidades).

### Para mirar la base de datos directamente
Con el programa ya ejecutado:
```bash
docker compose exec db psql -U redes -d tarea2
```
Algunas consultas útiles:
```sql
SELECT * FROM sismo;                                     -- el terremoto cargado
SELECT id, nombre, roles FROM nodos_clave;               -- los 24 nodos clave
SELECT capa, count(*), max(prob_falla)
FROM red_noded GROUP BY capa;                            -- enlaces y probabilidad máxima por capa
```
Tablas principales: `red_noded` (enlaces, con `source`/`target`, `prob_falla`, `sintetico`), `red_noded_vertices_pgr` (vértices de la topología), `nodos_clave`, `sismo` y `parametros_modelo`. También se puede conectar con otro programa en `localhost:5433` (usuario `redes`, clave `redes`, base `tarea2`).

## 8. Límites del trabajo

- La red es la reportada en 2016–2018, no la de 2010; no incluye el cable submarino Fibra Óptica Austral (2020) ni los anillos urbanos.
- RF es una cota inferior y RE una cota superior de la conectividad real.
- El modelo usa un punto como fuente del terremoto, falla cada enlace de forma independiente y no incluye tsunami, puentes ni energía eléctrica. Los detalles están en la sección de Discusión del informe.

## 9. Fuentes

Archivo SAIP AN002T0005610 (carta SUBTEL ORD. 7479/G); Estudio de NIC Chile (2018); evento USGS `official20100227063411530_30`; PeeringDB y submarinecablemap (nodos clave); Saragoni, Astroza y Ruiz (2004), Tabla 1, ec. (2); Isoyama et al. (2000), ec. (5) y Tabla 3. La lista completa está en `referencias.bib` y en el informe.

## 10. Problemas frecuentes

- **Puerto 5433 u 8000 ocupado**: cambiar el puerto en `docker-compose.yml`.
- **`permission denied` con Docker en Linux**: ejecutar `sudo usermod -aG docker $USER` y volver a iniciar sesión.
- **El mapa se ve sin fondo**: necesita conexión a internet.
- **`mapa/index.html` aparece modificado en git tras ejecutar**: es normal, el programa que genera el mapa escribe identificadores aleatorios; el contenido es el mismo.
- **Compilar el informe**: `latexmk -pdf main.tex` (la bibliografía está incluida en `main.tex`; solo se necesita ese archivo y la carpeta `figuras/`).
