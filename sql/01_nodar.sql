-- Paso 1 del nodado: disuelve solapes/duplicados y parte las lineas en cada cruce exacto.
-- (pgr_nodeNetwork falla sobre `red` con "Splitter line has linear intersection with input":
--  hay tramos colineales repetidos, p. ej. fibra con ids duplicados.)
-- Cada pieza hereda la capa de mayor prioridad que la cubre: fibra > postacion > camino > ferry.
DROP TABLE IF EXISTS red_pieza CASCADE;
CREATE TABLE red_pieza AS
WITH u AS (
  SELECT (ST_Dump(ST_UnaryUnion(ST_Collect(geom)))).geom AS geom FROM red
), p AS (
  SELECT row_number() OVER ()::int AS id, geom FROM u WHERE ST_GeometryType(geom) = 'ST_LineString'
)
SELECT p.id, p.geom, c.capa, c.sintetico
FROM p
CROSS JOIN LATERAL (
  SELECT r.capa, r.sintetico
  FROM red r
  WHERE ST_DWithin(r.geom, ST_LineInterpolatePoint(p.geom, 0.5), 0.000001)
  ORDER BY array_position(ARRAY['fibra','postacion','camino','ferry'], r.capa)
  LIMIT 1
) c;
ALTER TABLE red_pieza ADD PRIMARY KEY (id);
CREATE INDEX red_pieza_gix ON red_pieza USING gist (geom);
