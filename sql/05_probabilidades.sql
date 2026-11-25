-- Probabilidad de falla de cada enlace. Distancias en metros con geography (no en grados).
-- Cada enlace se parte en tramos <= largo_tramo_m; la tasa de cortes se evalua en el punto medio de
-- cada tramo y p_e = 1 - exp(-sum R(alfa_k) * l_k) (proceso de Poisson a lo largo del enlace).
WITH q AS (SELECT geom, profundidad_km h, LEAST(mag, par('ms_max')) ms FROM sismo ORDER BY mag DESC LIMIT 1),
tramos AS (
  SELECT e.id, s.geom g
  FROM red_noded e
  JOIN parametros_capas pc ON pc.capa = e.capa AND pc.expuesta,
  LATERAL ST_DumpSegments(ST_Segmentize(e.the_geom::geography, par('largo_tramo_m'))::geometry) s
), calc AS (
  SELECT t.id,
         ST_Length(t.g::geography) / 1000 l_km,
         sqrt(power(ST_Distance(ST_LineInterpolatePoint(t.g, 0.5)::geography, q.geom::geography) / 1000, 2)
              + power(q.h, 2)) r_km,
         q.ms
  FROM tramos t, q
), agg AS (
  SELECT id, sum(tasa_cortes_km(pga_cms2(r_km, ms)) * l_km) lam, max(pga_cms2(r_km, ms)) pga
  FROM calc GROUP BY id
)
UPDATE red_noded e
SET tasa_cortes = a.lam, prob_falla = 1 - exp(-a.lam), pga_max_cms2 = a.pga,
    dist_epi_km = ST_Distance(e.the_geom::geography, (SELECT geom FROM sismo ORDER BY mag DESC LIMIT 1)::geography) / 1000
FROM agg a WHERE a.id = e.id;

-- capas sin exposicion (ferry): probabilidad 0 por definicion del modelo
UPDATE red_noded e SET prob_falla = 0, tasa_cortes = 0, pga_max_cms2 = NULL,
    dist_epi_km = ST_Distance(e.the_geom::geography, (SELECT geom FROM sismo ORDER BY mag DESC LIMIT 1)::geography) / 1000
FROM parametros_capas pc WHERE pc.capa = e.capa AND NOT pc.expuesta;
