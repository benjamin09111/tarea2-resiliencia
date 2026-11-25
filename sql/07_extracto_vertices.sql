-- Extracto de la tabla de vertices: los primeros nodos clave con su vertice y el grado (aristas incidentes).
SELECT v.id, n.nombre,
       (SELECT count(*) FROM red_noded e WHERE e.source = v.id OR e.target = v.id) AS grado,
       round(ST_X(v.the_geom)::numeric, 4) AS lon, round(ST_Y(v.the_geom)::numeric, 4) AS lat
FROM red_noded_vertices_pgr v JOIN nodos_clave n ON n.vertice_id = v.id
ORDER BY n.id LIMIT 3;
