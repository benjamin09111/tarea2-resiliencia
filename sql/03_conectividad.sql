-- Reporte de conectividad (sin acometidas: estado de los datos SAIP). Ejecutar antes de F3.
\i /work/sql/03_componentes.sql

\echo '== Vertices y componentes'
SELECT (SELECT count(*) FROM red_noded_vertices_pgr) vertices,
       (SELECT count(*) FROM red_noded) aristas,
       (SELECT count(DISTINCT comp_rf) FROM red_noded_vertices_pgr) componentes_rf,
       (SELECT count(DISTINCT comp_re) FROM red_noded_vertices_pgr) componentes_re;

\echo '== 10 mayores componentes RF (km de fibra, latitudes extremas)'
SELECT v.comp_rf componente, count(*) aristas, round(sum(e.largo_km)::numeric,1) km,
       round(min(ST_YMin(e.the_geom))::numeric,2) lat_min, round(max(ST_YMax(e.the_geom))::numeric,2) lat_max
FROM red_noded e JOIN red_noded_vertices_pgr v ON v.id = e.source
WHERE e.capa = 'fibra' GROUP BY 1 ORDER BY km DESC LIMIT 10;

\echo '== Componentes RF de una sola arista y km que suman'
SELECT count(*) componentes_1_arista, round(sum(km)::numeric,1) km FROM (
  SELECT v.comp_rf, count(*) n, sum(e.largo_km) km FROM red_noded e JOIN red_noded_vertices_pgr v ON v.id = e.source
  WHERE e.capa='fibra' GROUP BY 1 HAVING count(*) = 1) t;

\echo '== 10 mayores componentes RE'
SELECT v.comp_re componente, count(*) aristas, round(sum(e.largo_km)::numeric,1) km,
       round(min(ST_YMin(e.the_geom))::numeric,2) lat_min, round(max(ST_YMax(e.the_geom))::numeric,2) lat_max
FROM red_noded e JOIN red_noded_vertices_pgr v ON v.id = e.source
GROUP BY 1 ORDER BY km DESC LIMIT 10;

\echo '== Callejones (vertices con cnt = 1) por escenario'
SELECT count(*) FILTER (WHERE cnt = 1) callejones_total, count(*) vertices FROM red_noded_vertices_pgr;
