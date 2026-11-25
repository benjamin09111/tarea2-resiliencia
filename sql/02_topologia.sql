-- Topologia de red: red_noded (aristas) + red_noded_vertices_pgr (vertices), tolerancia 0,0001 grados.
-- Las aristas son las piezas de sql/01_nodar.sql. Columna de falla en 0 por defecto (rubrica 2.0).
\i /work/sql/02_red_noded.sql
SELECT pgr_analyzeGraph('red_noded', 0.0001, 'the_geom', 'id', 'source', 'target');
\d red_noded_vertices_pgr
SELECT id, cnt, round(ST_X(the_geom)::numeric, 4) AS lon, round(ST_Y(the_geom)::numeric, 4) AS lat
FROM red_noded_vertices_pgr ORDER BY id LIMIT 3;
SELECT capa, count(*) aristas, round(sum(largo_km)::numeric,1) km, min(prob_falla), max(prob_falla)
FROM red_noded GROUP BY capa ORDER BY capa;
