-- Interpretacion del ATTR en operacion (RF): para cada grupo de nodos clave (componente RF), km de fibra
-- de la componente y distancia (km, geodesica) a la fibra mas cercana de otra componente con nodos clave.
WITH g AS (
  SELECT comp_rf, string_agg(id, ' ' ORDER BY id) nodos, count(*) n FROM nodos_clave GROUP BY comp_rf
), fib AS (
  SELECT v.comp_rf, ST_Collect(e.the_geom) geom, sum(e.largo_km) km
  FROM red_noded e JOIN red_noded_vertices_pgr v ON v.id = e.source
  WHERE e.capa = 'fibra' AND v.comp_rf IN (SELECT comp_rf FROM g) GROUP BY v.comp_rf
)
SELECT g.nodos, g.n, round(a.km::numeric) km_fibra,
       (SELECT round((min(ST_Distance(a.geom::geography, b.geom::geography)) / 1000)::numeric, 1)
        FROM fib b WHERE b.comp_rf <> a.comp_rf) brecha_min_km,
       (SELECT g2.nodos FROM fib b JOIN g g2 ON g2.comp_rf = b.comp_rf WHERE b.comp_rf <> a.comp_rf
        ORDER BY ST_Distance(a.geom::geography, b.geom::geography) LIMIT 1) vecino_mas_cercano
FROM g JOIN fib a USING (comp_rf) ORDER BY g.n DESC, g.nodos;
