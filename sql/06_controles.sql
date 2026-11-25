\echo '== Rango de prob_falla (debe estar en [0,1])'
SELECT min(prob_falla) p_min, max(prob_falla) p_max, count(*) enlaces FROM red_noded;
\echo '== Enlaces y km por rango de p y capa'
SELECT capa,
  count(*) FILTER (WHERE prob_falla = 0) p_0,
  count(*) FILTER (WHERE prob_falla > 0 AND prob_falla <= 0.1) p_0_01,
  count(*) FILTER (WHERE prob_falla > 0.1 AND prob_falla <= 0.5) p_01_05,
  count(*) FILTER (WHERE prob_falla > 0.5 AND prob_falla <= 0.9) p_05_09,
  count(*) FILTER (WHERE prob_falla > 0.9) p_09_1,
  round((sum(largo_km) FILTER (WHERE prob_falla = 0))::numeric) km_p0,
  round((sum(largo_km) FILTER (WHERE prob_falla > 0.5))::numeric) km_p_mayor_05
FROM red_noded GROUP BY capa ORDER BY capa;
\echo '== Distancia maxima al epicentro con p > 0 y minima con p = 0 (solo capas expuestas)'
SELECT round((max(dist_epi_km) FILTER (WHERE prob_falla > 0))::numeric, 1) max_dist_p_pos,
       round((min(dist_epi_km) FILTER (WHERE prob_falla = 0 AND capa <> 'ferry'))::numeric, 1) min_dist_p_cero
FROM red_noded;
\echo '== Valores de control del modelo (Ms = 8,5; h = 22,9 km)'
SELECT d_km, round(pga_cms2(sqrt(d_km^2 + 22.9^2), 8.5)::numeric) pga_cms2,
       round((pga_cms2(sqrt(d_km^2 + 22.9^2), 8.5) / 981)::numeric, 2) pga_g,
       round(tasa_cortes_km(pga_cms2(sqrt(d_km^2 + 22.9^2), 8.5))::numeric, 4) cortes_km
FROM (VALUES (50),(100),(200),(300),(400),(500),(600)) t(d_km);
\echo '== PGA y p en los nodos clave: distancia al epicentro y PGA del modelo'
SELECT n.id, n.nombre, round((ST_Distance(n.geom::geography, s.geom::geography)/1000)::numeric) d_epi_km,
       round(pga_cms2(sqrt(power(ST_Distance(n.geom::geography, s.geom::geography)/1000, 2) + s.profundidad_km^2), LEAST(s.mag, par('ms_max')))::numeric) pga_cms2
FROM nodos_clave n, sismo s ORDER BY 3;
