-- Construye red_noded (aristas) y su topologia, de forma determinista: las filas se escriben
-- ordenadas por id, porque pgr_createTopology elige los vertices segun el orden fisico de las filas.
-- Columna de falla en 0 por defecto (rubrica 2.0). Tolerancia 0,0001 grados.
DROP TABLE IF EXISTS red_noded CASCADE;
DROP TABLE IF EXISTS red_noded_vertices_pgr CASCADE;
CREATE TABLE red_noded AS
SELECT id, capa, sintetico, geom AS the_geom, ST_Length(geom::geography) / 1000 AS largo_km
FROM red_pieza ORDER BY id;
ALTER TABLE red_noded ADD PRIMARY KEY (id);
ALTER TABLE red_noded
  ADD COLUMN source integer, ADD COLUMN target integer,
  ADD COLUMN prob_falla double precision NOT NULL DEFAULT 0 CHECK (prob_falla BETWEEN 0 AND 1),
  ADD COLUMN tasa_cortes double precision,
  ADD COLUMN pga_max_cms2 double precision,
  ADD COLUMN dist_epi_km double precision;
CREATE INDEX red_noded_gix ON red_noded USING gist (the_geom);
SELECT pgr_createTopology('red_noded', 0.0001, 'the_geom', 'id', 'source', 'target', clean := true);
